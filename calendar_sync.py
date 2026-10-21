"""Google Calendar sync. A side effect only — it never blocks saving an item.

Mirrors an item's due date as a calendar event: a timed event if due has a
time, an all-day event if it doesn't. Deletes the event once the item is
done or parked. Any failure (no credentials yet, no network, API error) is
logged and swallowed, same philosophy as ai.py.
"""
import logging
from datetime import datetime, timedelta

import config
import store

log = logging.getLogger(__name__)

_service = None


def _get_service():
    """Build (and cache) an authorized Calendar API client, or None."""
    global _service
    if _service is not None:
        return _service
    if not config.GOOGLE_CREDENTIALS_PATH.exists():
        return None
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None
        if config.GOOGLE_TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(
                str(config.GOOGLE_TOKEN_PATH), config.GOOGLE_SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(config.GOOGLE_CREDENTIALS_PATH), config.GOOGLE_SCOPES)
                creds = flow.run_local_server(port=0)
            config.GOOGLE_TOKEN_PATH.write_text(creds.to_json())
        _service = build("calendar", "v3", credentials=creds)
        return _service
    except Exception:
        log.exception("Google Calendar auth failed")
        return None


def _event_body(item):
    """Build the Calendar API event body for an item. due must not be None."""
    due = item["due"]
    body = {"summary": item["title"], "description": item.get("done_def") or ""}
    if "T" in due:
        start = datetime.fromisoformat(due)
        minutes = item.get("est_minutes") or config.DEFAULT_EVENT_MINUTES
        end = start + timedelta(minutes=minutes)
        body["start"] = {"dateTime": start.isoformat(), "timeZone": config.TIMEZONE}
        body["end"] = {"dateTime": end.isoformat(), "timeZone": config.TIMEZONE}
    else:
        body["start"] = {"date": due}
        body["end"] = {"date": due}
    return body


def _find_clashes(service, item):
    """Other events overlapping a timed item's slot, as a list of titles."""
    due = item["due"]
    if "T" not in due:
        return []
    start = datetime.fromisoformat(due)
    minutes = item.get("est_minutes") or config.DEFAULT_EVENT_MINUTES
    end = start + timedelta(minutes=minutes)
    events = service.events().list(
        calendarId=config.GOOGLE_CALENDAR_ID,
        timeMin=start.isoformat(), timeMax=end.isoformat(),
        singleEvents=True).execute().get("items", [])
    return [e["summary"] for e in events
            if e.get("id") != item.get("calendar_id") and e.get("summary")]


def sync_due(item):
    """Create, update or delete this item's event to match its due date.

    Returns a list of clash titles (possibly empty) after a create/update,
    or None if calendar sync isn't configured or the API call failed.
    """
    service = _get_service()
    if service is None:
        return None
    try:
        should_delete = item["due"] is None or item["status"] in ("done", "parked")
        if should_delete:
            if item.get("calendar_id"):
                try:
                    service.events().delete(
                        calendarId=config.GOOGLE_CALENDAR_ID,
                        eventId=item["calendar_id"]).execute()
                except Exception:
                    log.exception("Calendar delete failed for item %s", item["id"])
                store.set_calendar_id(item["id"], None)
            return []

        clashes = _find_clashes(service, item)
        body = _event_body(item)
        if item.get("calendar_id"):
            service.events().update(
                calendarId=config.GOOGLE_CALENDAR_ID,
                eventId=item["calendar_id"], body=body).execute()
        else:
            event = service.events().insert(
                calendarId=config.GOOGLE_CALENDAR_ID, body=body).execute()
            store.set_calendar_id(item["id"], event["id"])
        return clashes
    except Exception:
        log.exception("Calendar sync failed for item %s", item["id"])
        return None

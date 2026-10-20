"""The only module that touches the database.

Holds the schema, every validation rule (V1-V10 in the spec) and every query.
Pages, the MCP server and ai.py call these functions and never write SQL.
"""
import json
import re
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import config

TZ = ZoneInfo(config.TIMEZONE)
_db_path = config.DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id          INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,
    note        TEXT,
    path        TEXT,
    status      TEXT NOT NULL DEFAULT 'inbox',
    done_def    TEXT,
    due         TEXT,
    est_minutes INTEGER,
    proposal    TEXT,
    calendar_id TEXT,
    created_at  TEXT,
    updated_at  TEXT,
    done_at     TEXT
);
CREATE TABLE IF NOT EXISTS updates (
    id        INTEGER PRIMARY KEY,
    item_id   INTEGER NOT NULL REFERENCES items(id),
    at        TEXT,
    text      TEXT NOT NULL,
    outcome   TEXT NOT NULL,
    next_step TEXT,
    next_due  TEXT
);
"""

PATH_SEGMENT = re.compile(r"^[A-Za-z0-9 -]+$")


class ValidationError(Exception):
    """Raised when input breaks a rule. `messages` are plain-language."""

    def __init__(self, messages):
        if isinstance(messages, str):
            messages = [messages]
        self.messages = list(messages)
        super().__init__("; ".join(self.messages))


# ---------- setup and small helpers ----------

def init_db(path=None):
    """Point the store at a database file and create the tables."""
    global _db_path
    if path is not None:
        _db_path = path
    _db_path_parent = getattr(_db_path, "parent", None)
    if _db_path_parent is not None:
        _db_path_parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.executescript(SCHEMA)


def _connect():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _now():
    return datetime.now(TZ)


def now_ts():
    """Current time as an ISO 8601 string in Johannesburg time."""
    return _now().isoformat(timespec="seconds")


def _row(row):
    """Turn a database row into a plain dict (proposal parsed from JSON)."""
    if row is None:
        return None
    item = dict(row)
    if "proposal" in item and item["proposal"]:
        try:
            item["proposal"] = json.loads(item["proposal"])
        except ValueError:
            item["proposal"] = None
    return item


def _clean(value):
    """Trim text; blank becomes None."""
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def due_for_input(due):
    """Format a stored due value for a form field ('YYYY-MM-DD[ HH:MM]')."""
    if not due:
        return ""
    return due[:16].replace("T", " ")


# ---------- validation helpers ----------

def parse_due(value, label="Due date", existing=None):
    """V3: read a date as Johannesburg time; return the ISO string.

    Returns None if blank. Raises ValidationError if malformed or in the
    past. A value equal to `existing` skips the past check, so an overdue
    item can still be edited.
    """
    value = _clean(value)
    if value is None:
        return None
    if existing and value == existing:
        return value
    for fmt, has_time in (("%Y-%m-%d", False), ("%Y-%m-%d %H:%M", True),
                          ("%Y-%m-%dT%H:%M", True)):
        try:
            parsed = datetime.strptime(value[:16] if has_time else value, fmt)
            break
        except ValueError:
            continue
    else:
        raise ValidationError(
            f"{label} must look like 2026-10-25 or 2026-10-25 14:30")
    parsed = parsed.replace(tzinfo=TZ)
    if has_time:
        if parsed < _now().replace(second=0, microsecond=0):
            raise ValidationError(f"{label} is in the past")
        return parsed.isoformat(timespec="minutes")
    if parsed.date() < _now().date():
        raise ValidationError(f"{label} is in the past")
    return parsed.strftime("%Y-%m-%d")


def _check_path(path):
    """Return an error message if the path is invalid, else None."""
    pillars = ", ".join(config.PILLARS[:-1]) + " or " + config.PILLARS[-1]
    path = _clean(path)
    if path is None:
        return f"Pick an area: {pillars}"
    parts = [p.strip() for p in path.split("/")]
    if parts[0] not in config.PILLARS:
        return f"Pick an area: {pillars}"
    if len(parts) > config.PATH_MAX_SEGMENTS:
        return f"Path can have at most {config.PATH_MAX_SEGMENTS} parts"
    if not all(p and PATH_SEGMENT.match(p) for p in parts):
        return "Path parts can only use letters, numbers, spaces and hyphens"
    return None


def _clean_path(path):
    return "/".join(p.strip() for p in path.split("/"))


def _to_minutes(value):
    """Coerce est_minutes from a form string; raise on junk."""
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError("Estimated minutes must be a whole number")


def _check_triage(conn, item, path, status, due, done_def, est_minutes):
    """V2, V3, V4, V5: validate a triage and return the clean field values."""
    errors = []
    path = _clean(path)
    msg = _check_path(path)
    if msg:
        errors.append(msg)
    elif path:
        path = _clean_path(path)

    if status not in config.CONFIRM_STATUSES:
        errors.append("Status must be one of: "
                      + ", ".join(config.CONFIRM_STATUSES))

    try:
        due = parse_due(due, existing=item["due"])
    except ValidationError as e:
        errors.extend(e.messages)
        due = None

    done_def = _clean(done_def)
    try:
        est = _to_minutes(est_minutes)
    except ValidationError as e:
        errors.extend(e.messages)
        est = None
    if est is not None and not config.EST_MIN <= est <= config.EST_MAX:
        errors.append(f"Estimated minutes must be between "
                      f"{config.EST_MIN} and {config.EST_MAX}")

    if status in config.CONFIRM_STATUSES and status != "parked":
        if due is None and not any("Due date" in e for e in errors):
            errors.append("Due date is missing")
        if not done_def or len(done_def) < config.DONE_DEF_MIN:
            errors.append("Done-definition is missing "
                          f"(at least {config.DONE_DEF_MIN} characters)")

    if status == "now":  # V4
        current = conn.execute(
            "SELECT id, title FROM items WHERE status='now' AND id != ?",
            (item["id"],)).fetchone()
        if current:
            errors.append(f"'{current['title']}' is NOW. "
                          "Finish or move it first.")
    if status == "next":  # V5
        count = conn.execute(
            "SELECT COUNT(*) FROM items WHERE status='next' AND id != ?",
            (item["id"],)).fetchone()[0]
        if count >= config.NEXT_CAP:
            errors.append(f"NEXT is full ({config.NEXT_CAP} items). "
                          "Move one out first.")

    if errors:
        raise ValidationError(errors)
    return dict(path=path, status=status, due=due,
                done_def=done_def, est_minutes=est)


def _load(conn, item_id, allow_done=False):
    """Fetch an item or raise; V8 blocks done items unless allowed."""
    row = conn.execute("SELECT * FROM items WHERE id=?",
                       (item_id,)).fetchone()
    if row is None:
        raise ValidationError("That item does not exist")
    if row["status"] == "done" and not allow_done:
        raise ValidationError("Done items are final and cannot be changed")
    return row


# ---------- writes ----------

def capture(title, note=None):
    """V1: save a new item to the inbox."""
    title = _clean(title)
    if title is None:
        raise ValidationError("Title is missing")
    if len(title) > config.TITLE_MAX:
        raise ValidationError(
            f"Title is too long (max {config.TITLE_MAX} characters)")
    ts = now_ts()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO items (title, note, status, created_at, updated_at)"
            " VALUES (?, ?, 'inbox', ?, ?)", (title, _clean(note), ts, ts))
        return _row(conn.execute("SELECT * FROM items WHERE id=?",
                                 (cur.lastrowid,)).fetchone())


def confirm(item_id, path, status, due=None, done_def=None, est_minutes=None):
    """V2-V5, V8: triage an item (also used to edit a triaged item)."""
    with _connect() as conn:
        item = _load(conn, item_id)
        f = _check_triage(conn, item, path, status, due, done_def,
                          est_minutes)
        conn.execute(
            "UPDATE items SET path=?, status=?, due=?, done_def=?, "
            "est_minutes=?, updated_at=? WHERE id=?",
            (f["path"], f["status"], f["due"], f["done_def"],
             f["est_minutes"], now_ts(), item_id))
        return _row(conn.execute("SELECT * FROM items WHERE id=?",
                                 (item_id,)).fetchone())


edit_item = confirm  # the detail page uses the same rules


def set_status(item_id, status):
    """Move an item between now/next/later/parked with the same checks."""
    if status not in ("now", "next", "later", "parked"):
        raise ValidationError("Status must be one of: now, next, later, parked")
    with _connect() as conn:
        item = _load(conn, item_id)
        f = _check_triage(conn, item, item["path"], status, item["due"],
                          item["done_def"], item["est_minutes"])
        conn.execute("UPDATE items SET status=?, updated_at=? WHERE id=?",
                     (f["status"], now_ts(), item_id))
        return _row(conn.execute("SELECT * FROM items WHERE id=?",
                                 (item_id,)).fetchone())


def add_update(item_id, text, outcome, next_step=None, next_due=None):
    """V6-V8: log an update and apply its effects, all in one transaction."""
    with _connect() as conn:
        item = _load(conn, item_id)
        errors = []
        text = _clean(text)
        if not text:
            errors.append("Update text is missing")
        if outcome not in config.OUTCOMES:
            errors.append("Outcome must be one of: "
                          + ", ".join(config.OUTCOMES))
        next_step = _clean(next_step)
        if outcome in ("small_problem", "big_problem"):
            if not next_step:
                errors.append("Next step is missing")
            try:
                next_due = parse_due(next_due, label="Next date")
            except ValidationError as e:
                errors.extend(e.messages)
                next_due = None
            else:
                if next_due is None:
                    errors.append("Next date is missing")
        else:
            next_step, next_due = None, None
        if errors:
            raise ValidationError(errors)

        ts = now_ts()
        conn.execute(
            "INSERT INTO updates (item_id, at, text, outcome, next_step, "
            "next_due) VALUES (?, ?, ?, ?, ?, ?)",
            (item_id, ts, text, outcome, next_step, next_due))
        if outcome == "done":
            conn.execute("UPDATE items SET status='done', done_at=?, "
                         "updated_at=? WHERE id=?", (ts, ts, item_id))
        elif outcome == "small_problem":
            conn.execute("UPDATE items SET due=?, updated_at=? WHERE id=?",
                         (next_due, ts, item_id))
        elif outcome == "big_problem":
            conn.execute("UPDATE items SET status='blocked', due=?, "
                         "updated_at=? WHERE id=?", (next_due, ts, item_id))
        else:
            conn.execute("UPDATE items SET updated_at=? WHERE id=?",
                         (ts, item_id))
        return _row(conn.execute("SELECT * FROM items WHERE id=?",
                                 (item_id,)).fetchone())


def discard(item_id):
    """V9: delete an item, but only while it is still in the inbox."""
    with _connect() as conn:
        item = _load(conn, item_id, allow_done=True)
        if item["status"] != "inbox":
            raise ValidationError("Only inbox items can be discarded")
        conn.execute("DELETE FROM updates WHERE item_id=?", (item_id,))
        conn.execute("DELETE FROM items WHERE id=?", (item_id,))


def save_proposal(item_id, proposal):
    """V10: store an AI proposal for display. Touches no other field."""
    with _connect() as conn:
        _load(conn, item_id, allow_done=True)
        conn.execute("UPDATE items SET proposal=? WHERE id=?",
                     (json.dumps(proposal) if proposal else None, item_id))


# ---------- queries ----------

def get_item(item_id):
    with _connect() as conn:
        return _row(conn.execute("SELECT * FROM items WHERE id=?",
                                 (item_id,)).fetchone())


def get_updates(item_id):
    """Update history for an item, newest first."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM updates WHERE item_id=? "
                            "ORDER BY id DESC", (item_id,)).fetchall()
        return [dict(r) for r in rows]


def list_items(status=None, path=None):
    """Items filtered by status and/or path prefix, newest first."""
    sql, args = "SELECT * FROM items WHERE 1=1", []
    if status:
        sql += " AND status=?"
        args.append(status)
    if path:
        sql += " AND (path=? OR path LIKE ?)"
        args += [path, path + "/%"]
    sql += " ORDER BY id DESC"
    with _connect() as conn:
        return [_row(r) for r in conn.execute(sql, args).fetchall()]


def known_paths():
    """Seed paths plus any path already in use, sorted."""
    with _connect() as conn:
        rows = conn.execute("SELECT DISTINCT path FROM items "
                            "WHERE path IS NOT NULL").fetchall()
    return sorted(set(config.SEED_PATHS) | {r["path"] for r in rows})


def today():
    """What the Today page shows."""
    today_str = _now().strftime("%Y-%m-%d")
    since = (_now() - timedelta(hours=24)).isoformat(timespec="seconds")
    with _connect() as conn:
        def fetch(sql, *args):
            return [_row(r) for r in conn.execute(sql, args).fetchall()]
        now_rows = fetch("SELECT * FROM items WHERE status='now'")
        return {
            "now": now_rows[0] if now_rows else None,
            "due": fetch(
                "SELECT * FROM items WHERE status IN "
                "('next','later','blocked') AND due IS NOT NULL "
                "AND substr(due,1,10) <= ? ORDER BY due", today_str),
            "next": fetch("SELECT * FROM items WHERE status='next' "
                          "ORDER BY due"),
            "done_recent": fetch(
                "SELECT * FROM items WHERE status='done' AND done_at >= ? "
                "ORDER BY done_at DESC", since),
        }


def board():
    """Items grouped by pillar, then by status column. Parked is separate."""
    columns = ("now", "next", "later", "blocked")
    result = {p: {**{c: [] for c in columns}, "parked": []}
              for p in config.PILLARS}
    for item in list_items():
        if item["status"] in ("inbox", "done") or not item["path"]:
            continue
        pillar = item["path"].split("/")[0]
        if pillar not in result:
            continue
        key = "parked" if item["status"] == "parked" else item["status"]
        result[pillar][key].append(item)
    return result

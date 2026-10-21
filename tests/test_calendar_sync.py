"""calendar_sync.py must never raise and must work with no credentials."""
import calendar_sync
import config
import store


class FakeRequest:
    def __init__(self, result):
        self._result = result

    def execute(self):
        return self._result


class FakeEvents:
    def __init__(self, list_results=None):
        self.inserted = []
        self.updated = []
        self.deleted = []
        self._list_results = list_results or []

    def insert(self, calendarId, body):
        self.inserted.append((calendarId, body))
        return FakeRequest({"id": "evt-1", **body})

    def update(self, calendarId, eventId, body):
        self.updated.append((calendarId, eventId, body))
        return FakeRequest({"id": eventId, **body})

    def delete(self, calendarId, eventId):
        self.deleted.append((calendarId, eventId))
        return FakeRequest({})

    def list(self, calendarId, timeMin, timeMax, singleEvents):
        return FakeRequest({"items": self._list_results})


class FakeService:
    def __init__(self, list_results=None):
        self._events = FakeEvents(list_results)

    def events(self):
        return self._events


def confirm_timed(tmp_path, due="2026-10-25 14:00"):
    store.init_db(tmp_path / "t.db")
    item = store.capture("Fix heat press")
    return store.confirm(item["id"], "Waverley/Machines", "later",
                         due=due, done_def="Heat press fixed")


def test_no_credentials_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "GOOGLE_CREDENTIALS_PATH",
                        tmp_path / "no_such_file.json")
    item = confirm_timed(tmp_path)
    assert calendar_sync.sync_due(item) is None


def test_insert_creates_event_and_saves_id(monkeypatch, tmp_path):
    fake = FakeService()
    monkeypatch.setattr(calendar_sync, "_get_service", lambda: fake)
    item = confirm_timed(tmp_path)

    clashes = calendar_sync.sync_due(item)

    assert clashes == []
    assert len(fake.events().inserted) == 1
    assert store.get_item(item["id"])["calendar_id"] == "evt-1"


def test_update_uses_existing_calendar_id(monkeypatch, tmp_path):
    fake = FakeService()
    monkeypatch.setattr(calendar_sync, "_get_service", lambda: fake)
    item = confirm_timed(tmp_path)
    calendar_sync.sync_due(item)
    item = store.get_item(item["id"])  # now carries calendar_id

    calendar_sync.sync_due(item)

    assert fake.events().updated[0][1] == "evt-1"
    assert fake.events().inserted == [fake.events().inserted[0]]  # still just one


def test_delete_when_done(monkeypatch, tmp_path):
    fake = FakeService()
    monkeypatch.setattr(calendar_sync, "_get_service", lambda: fake)
    item = confirm_timed(tmp_path)
    calendar_sync.sync_due(item)
    item = store.add_update(item["id"], "Fixed it", "done")

    result = calendar_sync.sync_due(item)

    assert result == []
    assert fake.events().deleted == [("primary", "evt-1")]
    assert store.get_item(item["id"])["calendar_id"] is None


def test_delete_when_due_cleared(monkeypatch, tmp_path):
    fake = FakeService()
    monkeypatch.setattr(calendar_sync, "_get_service", lambda: fake)
    item = confirm_timed(tmp_path)
    calendar_sync.sync_due(item)
    item = store.confirm(item["id"], item["path"], "parked")

    calendar_sync.sync_due(item)

    assert fake.events().deleted == [("primary", "evt-1")]


def test_all_day_event_for_date_only_due(monkeypatch, tmp_path):
    fake = FakeService()
    monkeypatch.setattr(calendar_sync, "_get_service", lambda: fake)
    item = confirm_timed(tmp_path, due="2026-10-25")

    calendar_sync.sync_due(item)

    body = fake.events().inserted[0][1]
    assert body["start"] == {"date": "2026-10-25"}
    assert body["end"] == {"date": "2026-10-25"}


def test_clash_detection_excludes_own_event(monkeypatch, tmp_path):
    fake = FakeService(list_results=[
        {"id": "other-evt", "summary": "Dentist"},
        {"id": "evt-1", "summary": "Fix heat press"},
    ])
    monkeypatch.setattr(calendar_sync, "_get_service", lambda: fake)
    item = confirm_timed(tmp_path)
    item = dict(item, calendar_id="evt-1")

    clashes = calendar_sync.sync_due(item)

    assert clashes == ["Dentist"]

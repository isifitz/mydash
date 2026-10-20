"""Tests for store.py: every rule V1-V10 has an accept and a reject case."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

import config
import store


def today_plus(days=0):
    """A date string relative to today in Johannesburg."""
    d = datetime.now(ZoneInfo(config.TIMEZONE)) + timedelta(days=days)
    return d.strftime("%Y-%m-%d")


@pytest.fixture(autouse=True)
def db(tmp_path):
    """A fresh temporary database for every test."""
    store.init_db(tmp_path / "test.db")


def triage(title="Task", status="later", **kw):
    """Capture an item and confirm it with sensible defaults."""
    item = store.capture(title)
    args = dict(path="Waverley/Products", status=status,
                due=today_plus(1), done_def="It is finished")
    args.update(kw)
    return store.confirm(item["id"], **args)


def messages(excinfo):
    return " | ".join(excinfo.value.messages)


# V1 capture
def test_v1_capture_saves_to_inbox_and_trims():
    item = store.capture("  Fix heat press  ")
    assert item["title"] == "Fix heat press"
    assert item["status"] == "inbox"


def test_v1_capture_rejects_empty_and_long_title():
    with pytest.raises(store.ValidationError):
        store.capture("   ")
    with pytest.raises(store.ValidationError):
        store.capture("x" * 121)


# V2 confirm
def test_v2_confirm_accepts_complete_input():
    item = triage(status="next", est_minutes=90)
    assert item["status"] == "next"
    assert item["est_minutes"] == 90


def test_v2_parked_needs_only_a_path():
    item = store.capture("Idea")
    item = store.confirm(item["id"], path="Parked", status="parked")
    assert item["status"] == "parked"


def test_v2_rejects_missing_due_and_done_def_and_saves_nothing():
    item = store.capture("Task")
    with pytest.raises(store.ValidationError) as e:
        store.confirm(item["id"], path="Waverley", status="later")
    assert "Due date is missing" in messages(e)
    assert "done" in messages(e).lower()
    assert store.get_item(item["id"])["status"] == "inbox"


def test_v2_rejects_bad_path_status_and_estimate():
    item = store.capture("Task")
    good = dict(due=today_plus(1), done_def="Finished")
    for bad in [dict(path="Nowhere/x", status="later"),
                dict(path="Waverley/a/b/c", status="later"),
                dict(path="Waverley/bad!", status="later"),
                dict(path="Waverley", status="inbox"),
                dict(path="Waverley", status="later", est_minutes=2)]:
        with pytest.raises(store.ValidationError):
            store.confirm(item["id"], **{**good, **bad})


# V3 dates
def test_v3_accepts_date_and_datetime_and_today():
    assert triage(due=today_plus(0))["due"] == today_plus(0)
    item = triage(due=today_plus(2) + " 14:30")
    assert item["due"].startswith(today_plus(2) + "T14:30")


def test_v3_rejects_past_and_malformed_dates():
    for bad in ["2020-01-01", "tomorrow", "2030-13-40", today_plus(-1)]:
        with pytest.raises(store.ValidationError):
            triage(due=bad)


# V4 one NOW
def test_v4_one_now_accepted_and_second_rejected_naming_first():
    triage("Fix heat press", status="now")
    with pytest.raises(store.ValidationError) as e:
        triage("Other", status="now")
    assert "'Fix heat press' is NOW" in messages(e)


def test_v4_reconfirming_the_current_now_is_allowed():
    item = triage("Fix heat press", status="now")
    again = store.confirm(item["id"], path="Waverley", status="now",
                          due=today_plus(1), done_def="Press works")
    assert again["status"] == "now"


# V5 NEXT cap
def test_v5_three_next_ok_fourth_rejected():
    for n in range(3):
        triage(f"n{n}", status="next")
    with pytest.raises(store.ValidationError) as e:
        triage("n4", status="next")
    assert "NEXT" in messages(e)


# V6 update
def test_v6_update_accepts_progress():
    item = triage()
    store.add_update(item["id"], "Made a start", "progress")
    assert len(store.get_updates(item["id"])) == 1


def test_v6_update_rejects_missing_item_empty_text_bad_outcome():
    item = triage()
    with pytest.raises(store.ValidationError):
        store.add_update(999, "hi", "progress")
    with pytest.raises(store.ValidationError):
        store.add_update(item["id"], "  ", "progress")
    with pytest.raises(store.ValidationError):
        store.add_update(item["id"], "hi", "great")


# V7 outcome effects
def test_v7_done_sets_status_and_done_at():
    item = triage()
    done = store.add_update(item["id"], "Finished", "done")
    assert done["status"] == "done" and done["done_at"]


def test_v7_small_problem_moves_due_and_keeps_status():
    item = triage(status="next")
    out = store.add_update(item["id"], "Part missing", "small_problem",
                           next_step="Order part", next_due=today_plus(3))
    assert out["status"] == "next" and out["due"] == today_plus(3)


def test_v7_big_problem_blocks_with_review_date():
    item = triage(status="now")
    out = store.add_update(item["id"], "Stuck", "big_problem",
                           next_step="Search forums", next_due=today_plus(2))
    assert out["status"] == "blocked" and out["due"] == today_plus(2)


def test_v7_problems_require_next_step_and_date():
    item = triage()
    for outcome in ["small_problem", "big_problem"]:
        with pytest.raises(store.ValidationError):
            store.add_update(item["id"], "Trouble", outcome)
    assert store.get_item(item["id"])["status"] == "later"
    assert store.get_updates(item["id"]) == []


# V8 done is final
def test_v8_done_items_cannot_be_updated_or_retriaged():
    item = triage()
    store.add_update(item["id"], "Finished", "done")
    with pytest.raises(store.ValidationError):
        store.add_update(item["id"], "more", "progress")
    with pytest.raises(store.ValidationError):
        store.confirm(item["id"], path="Waverley", status="later",
                      due=today_plus(1), done_def="Again")
    with pytest.raises(store.ValidationError):
        store.set_status(item["id"], "now")


# V9 delete
def test_v9_discard_inbox_item():
    item = store.capture("Bad capture")
    store.discard(item["id"])
    assert store.get_item(item["id"]) is None


def test_v9_discard_rejects_triaged_item():
    item = triage()
    with pytest.raises(store.ValidationError):
        store.discard(item["id"])


# V10 proposals never applied automatically
def test_v10_saving_a_proposal_changes_no_item_fields():
    item = store.capture("DJ booth package")
    store.save_proposal(item["id"], {"path": "Waverley/Products",
                                     "status": "next", "due": today_plus(1)})
    after = store.get_item(item["id"])
    assert after["proposal"]
    assert after["path"] is None and after["status"] == "inbox"
    assert after["due"] is None


# set_status and queries
def test_set_status_moves_between_states_with_checks():
    item = triage(status="later")
    assert store.set_status(item["id"], "now")["status"] == "now"
    other = triage("Other")
    with pytest.raises(store.ValidationError):
        store.set_status(other["id"], "now")
    assert store.set_status(item["id"], "parked")["status"] == "parked"


def test_set_status_rejects_untriaged_item():
    item = store.capture("Loose")
    with pytest.raises(store.ValidationError):
        store.set_status(item["id"], "next")


def test_today_groups_items():
    now = triage("Now one", status="now", due=today_plus(0))
    triage("Next one", status="next")
    due = triage("Due today", status="later", due=today_plus(0))
    blocked = triage("Stuck", status="later")
    store.add_update(blocked["id"], "x", "big_problem",
                     next_step="look", next_due=today_plus(0))
    fin = triage("Finished")
    store.add_update(fin["id"], "ok", "done")
    t = store.today()
    assert t["now"]["id"] == now["id"]
    assert [i["title"] for i in t["next"]] == ["Next one"]
    assert {i["id"] for i in t["due"]} == {due["id"], blocked["id"]}
    assert [i["id"] for i in t["done_recent"]] == [fin["id"]]


def test_list_items_filters_and_known_paths():
    triage("A", path="Waverley/Machines")
    triage("B", path="Music/DJing", status="next")
    assert [i["title"] for i in store.list_items(status="next")] == ["B"]
    assert [i["title"] for i in store.list_items(path="Waverley")] == ["A"]
    assert "Waverley/Machines" in store.known_paths()
    assert "Waverley/Products" in store.known_paths()  # seed list

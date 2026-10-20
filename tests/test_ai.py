"""ai.py must never raise and must work with no API key."""
import ai
import store


def test_no_key_returns_none(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert ai.propose("Fix heat press") is None


def test_failure_returns_none(monkeypatch, tmp_path):
    store.init_db(tmp_path / "t.db")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "bad-key")

    def boom(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr("anthropic.resources.messages.Messages.create", boom)
    assert ai.propose("Fix heat press") is None


def test_propose_and_save_stores_blank_without_key(monkeypatch, tmp_path):
    store.init_db(tmp_path / "t.db")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    item = store.capture("Fix heat press")
    assert ai.propose_and_save(item["id"]) is None
    assert store.get_item(item["id"])["proposal"] is None

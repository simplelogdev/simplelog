"""Unit tests for creds_store.py."""
import creds_store


def test_load_missing_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(creds_store, "_DIR", tmp_path)
    assert creds_store.load("myprovider") == {}


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(creds_store, "_DIR", tmp_path)
    data = {"token": "abc123", "region": "eu-west-1"}
    creds_store.save("aws", data)
    assert creds_store.load("aws") == data


def test_save_creates_dir(tmp_path, monkeypatch):
    nested = tmp_path / "a" / "b"
    monkeypatch.setattr(creds_store, "_DIR", nested)
    creds_store.save("x", {"k": "v"})
    assert nested.is_dir()


def test_exists_false_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(creds_store, "_DIR", tmp_path)
    assert not creds_store.exists("ghost")


def test_exists_true_after_save(tmp_path, monkeypatch):
    monkeypatch.setattr(creds_store, "_DIR", tmp_path)
    creds_store.save("svc", {"a": 1})
    assert creds_store.exists("svc")


def test_clear_removes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(creds_store, "_DIR", tmp_path)
    creds_store.save("svc", {"a": 1})
    creds_store.clear("svc")
    assert not creds_store.exists("svc")


def test_clear_noop_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(creds_store, "_DIR", tmp_path)
    creds_store.clear("ghost")  # must not raise


def test_load_bad_json_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(creds_store, "_DIR", tmp_path)
    (tmp_path / "creds_bad.json").write_text("not-json")
    assert creds_store.load("bad") == {}


def test_save_overwrites_existing(tmp_path, monkeypatch):
    monkeypatch.setattr(creds_store, "_DIR", tmp_path)
    creds_store.save("s", {"v": 1})
    creds_store.save("s", {"v": 2})
    assert creds_store.load("s") == {"v": 2}

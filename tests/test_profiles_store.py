"""Unit tests for profiles_store.py."""
import profiles_store


def test_load_all_empty_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles_store, "_DIR", tmp_path)
    assert profiles_store.load_all("aws") == []


def test_upsert_inserts_new_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles_store, "_DIR", tmp_path)
    profiles_store.upsert("aws", "prod", {"region": "us-east-1"})
    profiles = profiles_store.load_all("aws")
    assert len(profiles) == 1
    assert profiles[0]["name"] == "prod"
    assert profiles[0]["region"] == "us-east-1"


def test_upsert_updates_existing_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles_store, "_DIR", tmp_path)
    profiles_store.upsert("aws", "prod", {"region": "us-east-1"})
    profiles_store.upsert("aws", "prod", {"region": "eu-west-1"})
    profiles = profiles_store.load_all("aws")
    assert len(profiles) == 1
    assert profiles[0]["region"] == "eu-west-1"


def test_upsert_multiple_profiles(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles_store, "_DIR", tmp_path)
    profiles_store.upsert("aws", "prod", {"region": "us-east-1"})
    profiles_store.upsert("aws", "dev", {"region": "eu-west-1"})
    profiles = profiles_store.load_all("aws")
    names = [p["name"] for p in profiles]
    assert "prod" in names
    assert "dev" in names


def test_upsert_new_profile_inserted_at_front(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles_store, "_DIR", tmp_path)
    profiles_store.upsert("svc", "first", {})
    profiles_store.upsert("svc", "second", {})
    profiles = profiles_store.load_all("svc")
    assert profiles[0]["name"] == "second"


def test_delete_removes_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles_store, "_DIR", tmp_path)
    profiles_store.upsert("aws", "prod", {"region": "us-east-1"})
    profiles_store.upsert("aws", "dev", {"region": "eu-west-1"})
    profiles_store.delete("aws", "prod")
    names = [p["name"] for p in profiles_store.load_all("aws")]
    assert "prod" not in names
    assert "dev" in names


def test_delete_noop_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles_store, "_DIR", tmp_path)
    profiles_store.delete("svc", "ghost")  # must not raise


def test_save_all_and_load_all_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles_store, "_DIR", tmp_path)
    data = [{"name": "a", "x": 1}, {"name": "b", "x": 2}]
    profiles_store.save_all("myservice", data)
    assert profiles_store.load_all("myservice") == data


def test_load_all_bad_json_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles_store, "_DIR", tmp_path)
    (tmp_path / "profiles_svc.json").write_text("not-json")
    assert profiles_store.load_all("svc") == []


def test_upsert_does_not_duplicate_name_key(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles_store, "_DIR", tmp_path)
    profiles_store.upsert("svc", "p1", {"name": "p1", "val": 42})
    profiles = profiles_store.load_all("svc")
    assert profiles[0].get("name") == "p1"
    assert list(profiles[0].keys()).count("name") == 1

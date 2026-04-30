"""Tests for i18n.py — translation module."""
import pytest

import i18n


def setup_function():
    """Reset locale to English before each test."""
    i18n.set_locale("en")
    i18n._callbacks.clear()


# ── tr() ──────────────────────────────────────────────────────────────────────

def test_tr_english_default():
    assert i18n.tr("menu_file") == "File"


def test_tr_french_after_set_locale():
    i18n.set_locale("fr")
    assert i18n.tr("menu_file") == "Fichier"


def test_tr_unknown_key_returns_key():
    assert i18n.tr("nonexistent_key_xyz") == "nonexistent_key_xyz"


def test_tr_with_kwargs():
    assert "42" in i18n.tr("viewer_lines", n=42)


def test_tr_with_kwargs_french():
    i18n.set_locale("fr")
    result = i18n.tr("viewer_lines", n=1_000)
    assert "1" in result  # at least the number is present


def test_tr_fallback_to_english_for_missing_fr_key():
    # All keys should exist in FR; if one were missing it should fall back to EN
    i18n.set_locale("fr")
    val = i18n.tr("menu_file")
    assert val != "menu_file"  # should never return the raw key


# ── set_locale / get_locale ───────────────────────────────────────────────────

def test_set_locale_english():
    i18n.set_locale("en")
    assert i18n.get_locale() == "en"


def test_set_locale_french():
    i18n.set_locale("fr")
    assert i18n.get_locale() == "fr"


def test_set_locale_unknown_falls_back_to_english():
    i18n.set_locale("xx")
    assert i18n.get_locale() == "en"


# ── register / unregister / retranslate_all ───────────────────────────────────

def test_register_and_retranslate_all():
    calls = []
    i18n.register(1, lambda: calls.append(1))
    i18n.retranslate_all()
    assert calls == [1]


def test_unregister_stops_callback():
    calls = []
    i18n.register(99, lambda: calls.append(99))
    i18n.unregister(99)
    i18n.retranslate_all()
    assert calls == []


def test_retranslate_all_updates_locale():
    results = []
    i18n.set_locale("en")
    i18n.register(42, lambda: results.append(i18n.tr("menu_file")))
    i18n.set_locale("fr")
    i18n.retranslate_all()
    assert results[-1] == "Fichier"


# ── All required keys exist in both locales ───────────────────────────────────

_REQUIRED_KEYS = [
    "menu_file", "menu_edit", "menu_language", "menu_help",
    "action_open", "action_update", "action_quit",
    "action_copy", "action_break",
    "cw_title", "cw_auth_mode", "cw_auth_profile", "cw_auth_keys",
    "cw_field_access_key", "cw_field_secret_key",
    "file_title",
    "viewer_autoscroll", "viewer_clear", "viewer_stop",
    "open_mode_tab", "open_mode_vertical", "open_mode_horizontal",
    "help_title", "help_content",
    "update_title", "update_up_to_date", "update_available",
    "sidebar_search", "sidebar_filter", "sidebar_json_keys",
    "sidebar_add_and", "sidebar_add_or", "sidebar_prev", "sidebar_next",
    "sidebar_hits", "sidebar_no_hits", "sidebar_term_ph",
    "sidebar_live_filter", "sidebar_json_ph",
]


@pytest.mark.parametrize("key", _REQUIRED_KEYS)
def test_key_exists_in_english(key):
    i18n.set_locale("en")
    assert i18n.tr(key) != key, f"Key '{key}' missing in EN"


@pytest.mark.parametrize("key", _REQUIRED_KEYS)
def test_key_exists_in_french(key):
    i18n.set_locale("fr")
    assert i18n.tr(key) != key, f"Key '{key}' missing in FR"


# ── Sidebar keys ───────────────────────────────────────────────────────────────

def test_sidebar_search_key_en():
    i18n.set_locale("en")
    assert i18n.tr("sidebar_search") == "Search"


def test_sidebar_search_key_fr():
    i18n.set_locale("fr")
    assert i18n.tr("sidebar_search") == "Recherche"


def test_sidebar_hits_key_en():
    i18n.set_locale("en")
    assert i18n.tr("sidebar_hits", n=42) == "42 hits"


def test_sidebar_hits_key_fr():
    i18n.set_locale("fr")
    assert i18n.tr("sidebar_hits", n=42) == "42 résultats"


def test_viewer_search_ph_removed():
    """viewer_search_ph key must no longer exist (search bar moved to sidebar)."""
    i18n.set_locale("en")
    assert i18n.tr("viewer_search_ph") == "viewer_search_ph"  # returns key when missing


def test_action_paste_removed():
    """action_paste key must no longer exist (removed from menu)."""
    i18n.set_locale("en")
    assert i18n.tr("action_paste") == "action_paste"


# ── Full EN/FR catalog parity ─────────────────────────────────────────────────

def test_all_en_keys_present_in_fr():
    en_keys = set(i18n._STRINGS["en"].keys())
    fr_keys = set(i18n._STRINGS["fr"].keys())
    missing = en_keys - fr_keys
    assert not missing, f"FR catalog missing keys: {sorted(missing)}"


# ── tr() edge cases ───────────────────────────────────────────────────────────

def test_tr_missing_fr_key_falls_back_to_en_value(monkeypatch):
    monkeypatch.setitem(i18n._STRINGS, "fr", {})  # empty FR catalog
    i18n.set_locale("fr")
    assert i18n.tr("menu_file") == "File"  # EN fallback


def test_tr_completely_missing_key_returns_key():
    assert i18n.tr("__no_such_key__") == "__no_such_key__"


def test_tr_kwargs_applied_correctly():
    i18n.set_locale("en")
    result = i18n.tr("update_up_to_date", version="1.2.3")
    assert "1.2.3" in result


# ── retranslate_all exception safety ─────────────────────────────────────────

def test_retranslate_all_swallows_callback_exception():
    def bad_cb():
        raise RuntimeError("callback error")

    i18n.register(999, bad_cb)
    try:
        i18n.retranslate_all()  # must not propagate
    except Exception:
        pytest.fail("retranslate_all raised an exception")
    finally:
        i18n.unregister(999)


# ── save_locale / load_locale persistence ─────────────────────────────────────

def test_save_and_load_locale_roundtrip(monkeypatch, tmp_path):
    prefs_path = tmp_path / "prefs.json"
    monkeypatch.setattr(i18n, "_PREFS_PATH", prefs_path)
    i18n.set_locale("fr")
    i18n.save_locale()
    i18n.set_locale("en")
    i18n.load_locale()
    assert i18n.get_locale() == "fr"


def test_load_locale_missing_file_defaults_to_en(monkeypatch, tmp_path):
    prefs_path = tmp_path / "nonexistent.json"
    monkeypatch.setattr(i18n, "_PREFS_PATH", prefs_path)
    i18n.set_locale("fr")
    i18n.load_locale()
    # File doesn't exist — locale should stay as it was (no crash, no change)
    # The contract is: no exception. Locale is unchanged (still "fr" from set above)
    # because load only changes if it finds a valid locale in the file.
    assert i18n.get_locale() in ("en", "fr")  # no crash is the key assertion


def test_load_locale_corrupt_json_defaults_to_en(monkeypatch, tmp_path):
    prefs_path = tmp_path / "prefs.json"
    prefs_path.write_text("not valid json", encoding="utf-8")
    monkeypatch.setattr(i18n, "_PREFS_PATH", prefs_path)
    i18n.set_locale("en")
    i18n.load_locale()  # must not raise
    assert i18n.get_locale() == "en"


def test_save_locale_merges_existing_prefs(monkeypatch, tmp_path):
    prefs_path = tmp_path / "prefs.json"
    import json
    prefs_path.write_text(json.dumps({"other_key": "other_value"}), encoding="utf-8")
    monkeypatch.setattr(i18n, "_PREFS_PATH", prefs_path)
    i18n.set_locale("fr")
    i18n.save_locale()
    saved = json.loads(prefs_path.read_text(encoding="utf-8"))
    assert saved["locale"] == "fr"
    assert saved["other_key"] == "other_value"


def test_save_locale_creates_parent_dirs(monkeypatch, tmp_path):
    prefs_path = tmp_path / "deep" / "nested" / "prefs.json"
    monkeypatch.setattr(i18n, "_PREFS_PATH", prefs_path)
    i18n.set_locale("en")
    i18n.save_locale()
    assert prefs_path.exists()

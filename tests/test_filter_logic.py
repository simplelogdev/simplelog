"""Unit tests for pure filter/search logic in ui.py."""
import os
import sys

# Prevent PyQt6 import during testing — we only need the module-level functions
# We import them via a shim after adding the project root to sys.path.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def _import_logic():
    """Import only after ensuring no display is needed."""
    import os as _os
    _os.environ.setdefault("DISPLAY", ":0")
    from ui import (
        TermRow,
        _classify_line,
        _extract_json_keys,
        _line_matches,
        _resolve_main_key,
        _try_parse_json,
    )
    return TermRow, _line_matches, _extract_json_keys, _try_parse_json, _classify_line, _resolve_main_key


# ── TermRow ───────────────────────────────────────────────────────────────────

def test_term_row_first_has_empty_operator():
    TermRow, *_ = _import_logic()
    t = TermRow(text="foo", operator="")
    assert t.operator == ""


# ── _line_matches ─────────────────────────────────────────────────────────────

def test_no_terms_matches_everything():
    _, _line_matches, *_ = _import_logic()
    assert _line_matches("anything here", []) is True


def test_single_term_match():
    TermRow, _line_matches, *_ = _import_logic()
    terms = [TermRow("error", "")]
    assert _line_matches("ERROR: disk full", terms) is True


def test_single_term_no_match():
    TermRow, _line_matches, *_ = _import_logic()
    terms = [TermRow("error", "")]
    assert _line_matches("INFO: all good", terms) is False


def test_case_insensitive():
    TermRow, _line_matches, *_ = _import_logic()
    terms = [TermRow("ERROR", "")]
    assert _line_matches("error: something", terms) is True


def test_and_both_match():
    TermRow, _line_matches, *_ = _import_logic()
    terms = [TermRow("error", ""), TermRow("disk", "AND")]
    assert _line_matches("ERROR: disk full", terms) is True


def test_and_second_missing():
    TermRow, _line_matches, *_ = _import_logic()
    terms = [TermRow("error", ""), TermRow("disk", "AND")]
    assert _line_matches("ERROR: memory full", terms) is False


def test_or_first_matches():
    TermRow, _line_matches, *_ = _import_logic()
    terms = [TermRow("error", ""), TermRow("warn", "OR")]
    assert _line_matches("ERROR: something", terms) is True


def test_or_second_matches():
    TermRow, _line_matches, *_ = _import_logic()
    terms = [TermRow("error", ""), TermRow("warn", "OR")]
    assert _line_matches("WARN: low memory", terms) is True


def test_or_neither_matches():
    TermRow, _line_matches, *_ = _import_logic()
    terms = [TermRow("error", ""), TermRow("warn", "OR")]
    assert _line_matches("INFO: all good", terms) is False


def test_empty_term_text_matches_all():
    TermRow, _line_matches, *_ = _import_logic()
    terms = [TermRow("", "")]  # empty text = match all
    assert _line_matches("anything", terms) is True


# ── _extract_json_keys ────────────────────────────────────────────────────────

def test_pure_json_object():
    _, _, _extract_json_keys, *_ = _import_logic()
    keys = _extract_json_keys('{"level": "ERROR", "msg": "fail", "userId": 42}')
    assert keys == {"level", "msg", "userId"}


def test_non_json_line_returns_empty_or_partial():
    _, _, _extract_json_keys, *_ = _import_logic()
    keys = _extract_json_keys("plain log line with no JSON")
    assert isinstance(keys, set)  # may be empty or have false positives, that's OK


def test_json_embedded_in_line():
    _, _, _extract_json_keys, *_ = _import_logic()
    line = '2024-01-01 ERROR {"requestId": "abc", "status": 500}'
    keys = _extract_json_keys(line)
    assert "requestId" in keys
    assert "status" in keys


def test_invalid_json_uses_fallback_regex():
    _, _, _extract_json_keys, *_ = _import_logic()
    # Not valid JSON but has "key": patterns
    line = '{"userId": 1, broken}'
    keys = _extract_json_keys(line)
    assert "userId" in keys


# ── KV matching ───────────────────────────────────────────────────────────────

def test_kv_match_exact():
    TermRow, _line_matches, *_ = _import_logic()
    terms = [TermRow(text="toto", operator="", key="skills")]
    assert _line_matches('{"skills": "toto", "source": "api"}', terms) is True


def test_kv_match_case_insensitive():
    TermRow, _line_matches, *_ = _import_logic()
    terms = [TermRow(text="TOTO", operator="", key="skills")]
    assert _line_matches('{"skills": "toto"}', terms) is True


def test_kv_match_partial():
    TermRow, _line_matches, *_ = _import_logic()
    terms = [TermRow(text="tot", operator="", key="skills")]
    assert _line_matches('{"skills": "toto"}', terms) is True


def test_kv_no_match_wrong_value():
    TermRow, _line_matches, *_ = _import_logic()
    terms = [TermRow(text="other", operator="", key="skills")]
    assert _line_matches('{"skills": "toto"}', terms) is False


def test_kv_no_match_not_json():
    TermRow, _line_matches, *_ = _import_logic()
    terms = [TermRow(text="toto", operator="", key="skills")]
    assert _line_matches("plain text line with toto", terms) is False


def test_kv_no_match_missing_key():
    TermRow, _line_matches, *_ = _import_logic()
    terms = [TermRow(text="toto", operator="", key="skills")]
    assert _line_matches('{"other": "toto"}', terms) is False


def test_kv_empty_text_matches_key_presence():
    TermRow, _line_matches, *_ = _import_logic()
    terms = [TermRow(text="", operator="", key="skills")]
    assert _line_matches('{"skills": "anything"}', terms) is True
    assert not _line_matches('{"other": "val"}', terms)


def test_kv_mixed_with_text_term_and():
    TermRow, _line_matches, *_ = _import_logic()
    terms = [
        TermRow(text="error", operator=""),
        TermRow(text="toto", operator="AND", key="skills"),
    ]
    assert _line_matches('error: {"skills": "toto"}', terms) is True
    assert not _line_matches('info: {"skills": "toto"}', terms)


def test_kv_numeric_value():
    TermRow, _line_matches, *_ = _import_logic()
    terms = [TermRow(text="401", operator="", key="status")]
    assert _line_matches('{"status": 401}', terms) is True


# ── _try_parse_json ────────────────────────────────────────────────────────────

def test_try_parse_json_valid():
    *_, _try_parse_json, _classify_line, _resolve_main_key = _import_logic()
    result = _try_parse_json('{"level": "ERROR", "msg": "fail"}')
    assert result == {"level": "ERROR", "msg": "fail"}

def test_try_parse_json_not_json():
    *_, _try_parse_json, _classify_line, _resolve_main_key = _import_logic()
    assert _try_parse_json("plain text") is None

def test_try_parse_json_array_returns_none():
    *_, _try_parse_json, _classify_line, _resolve_main_key = _import_logic()
    assert _try_parse_json('[1, 2, 3]') is None

def test_try_parse_json_invalid_returns_none():
    *_, _try_parse_json, _classify_line, _resolve_main_key = _import_logic()
    assert _try_parse_json('{broken}') is None

def test_try_parse_json_empty_object():
    *_, _try_parse_json, _classify_line, _resolve_main_key = _import_logic()
    assert _try_parse_json('{}') == {}


# ── _classify_line ─────────────────────────────────────────────────────────────

def test_classify_error():
    *_, _try_parse_json, _classify_line, _resolve_main_key = _import_logic()
    assert _classify_line("ERROR: disk full") == "error"

def test_classify_warn():
    *_, _try_parse_json, _classify_line, _resolve_main_key = _import_logic()
    assert _classify_line("WARN: low memory") == "warn"

def test_classify_info():
    *_, _try_parse_json, _classify_line, _resolve_main_key = _import_logic()
    assert _classify_line("INFO: server started") == "info"

def test_classify_debug():
    *_, _try_parse_json, _classify_line, _resolve_main_key = _import_logic()
    assert _classify_line("DEBUG: entering loop") == "debug"

def test_classify_trace():
    *_, _try_parse_json, _classify_line, _resolve_main_key = _import_logic()
    assert _classify_line("TRACE: span entered") == "trace"

def test_classify_plain():
    *_, _try_parse_json, _classify_line, _resolve_main_key = _import_logic()
    assert _classify_line("server listening on :3000") == "plain"

def test_classify_case_insensitive():
    *_, _try_parse_json, _classify_line, _resolve_main_key = _import_logic()
    assert _classify_line("error: something bad") == "error"

def test_classify_critical_is_error():
    *_, _try_parse_json, _classify_line, _resolve_main_key = _import_logic()
    assert _classify_line("CRITICAL: out of memory") == "error"


# ── _resolve_main_key ──────────────────────────────────────────────────────────

def test_resolve_main_key_message():
    *_, _try_parse_json, _classify_line, _resolve_main_key = _import_logic()
    assert _resolve_main_key({"message": "hello", "level": "INFO"}) == "message"

def test_resolve_main_key_msg():
    *_, _try_parse_json, _classify_line, _resolve_main_key = _import_logic()
    assert _resolve_main_key({"msg": "hello"}) == "msg"

def test_resolve_main_key_priority():
    *_, _try_parse_json, _classify_line, _resolve_main_key = _import_logic()
    # "message" beats "data"
    assert _resolve_main_key({"data": "x", "message": "y"}) == "message"

def test_resolve_main_key_none_when_no_standard_key():
    *_, _try_parse_json, _classify_line, _resolve_main_key = _import_logic()
    assert _resolve_main_key({"userId": "abc", "status": 200}) is None

def test_resolve_main_key_empty_dict():
    *_, _try_parse_json, _classify_line, _resolve_main_key = _import_logic()
    assert _resolve_main_key({}) is None

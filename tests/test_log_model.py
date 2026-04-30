"""Unit tests for LogModel — no GUI required."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("DISPLAY", ":0")


def _make_model():
    # LogModel needs a QApplication to exist for signal/slot machinery
    from PyQt6.QtWidgets import QApplication

    from ui import LogModel
    app = QApplication.instance() or QApplication(sys.argv)
    return LogModel(), app


def test_empty_model():
    model, _ = _make_model()
    assert model.rowCount() == 0


def test_append_plain_events():
    model, _ = _make_model()
    model.append_events([(0, "hello"), (0, "world")])
    assert model.rowCount() == 2


def test_append_json_event():
    from ui import _ITEM_ROLE
    model, _ = _make_model()
    model.append_events([(0, '{"message": "hi", "level": "INFO"}')])
    assert model.rowCount() == 1
    item = model.data(model.index(0), _ITEM_ROLE)
    assert item.is_json is True
    assert item.main_key == "message"


def test_json_keys_emitted():
    results = []
    model, _ = _make_model()
    model.json_keys_updated.connect(results.append)
    model.append_events([(0, '{"skills": "toto", "version": "1.0"}')])
    assert len(results) == 1
    assert "skills" in results[0]
    assert "version" in results[0]


def test_apply_filter_hides_non_matching():
    from ui import TermRow
    model, _ = _make_model()
    model.append_events([(0, "ERROR: bad"), (0, "INFO: good"), (0, "ERROR: also bad")])
    assert model.rowCount() == 3
    model.apply_filter([TermRow(text="ERROR", operator="")])
    assert model.rowCount() == 2


def test_apply_filter_empty_shows_all():
    model, _ = _make_model()
    model.append_events([(0, "ERROR: bad"), (0, "INFO: good")])
    model.apply_filter([])
    assert model.rowCount() == 2


def test_clear():
    model, _ = _make_model()
    model.append_events([(0, "a"), (0, "b")])
    model.clear()
    assert model.rowCount() == 0


def test_max_lines_enforced():
    model, _ = _make_model()
    model._MAX_LINES = 5
    events = [(0, f"line {i}") for i in range(10)]
    model.append_events(events)
    assert model.rowCount() <= 5


def test_kv_filter():
    from ui import TermRow
    model, _ = _make_model()
    model.append_events([
        (0, '{"skills": "toto", "level": "INFO"}'),
        (0, '{"skills": "other", "level": "INFO"}'),
        (0, "plain line"),
    ])
    model.apply_filter([TermRow(text="toto", operator="", key="skills")])
    assert model.rowCount() == 1


def test_expand_toggle():
    from ui import _EXPANDED_ROLE, _ITEM_ROLE
    model, _ = _make_model()
    model.append_events([(0, '{"message": "hi"}')])
    idx = model.index(0)
    item = model.data(idx, _ITEM_ROLE)
    assert item.expanded is False
    model.setData(idx, True, _EXPANDED_ROLE)
    assert item.expanded is True


def test_insert_break_adds_row():
    from ui import _ITEM_ROLE
    model, _ = _make_model()
    model.append_events([(0, "line 1"), (0, "line 2")])
    model.insert_break()
    assert model.rowCount() == 3
    item = model.data(model.index(2), _ITEM_ROLE)
    assert item.is_break is True
    assert "══" in item.message


def test_break_survives_filter():
    from ui import _ITEM_ROLE, TermRow
    model, _ = _make_model()
    model.append_events([(0, "ERROR: bad"), (0, "INFO: good")])
    model.insert_break()
    model.apply_filter([TermRow(text="ERROR", operator="")])
    # 1 matching line + 1 break
    assert model.rowCount() == 2
    items = [model.data(model.index(i), _ITEM_ROLE) for i in range(model.rowCount())]
    assert any(it.is_break for it in items)

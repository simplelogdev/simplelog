# UI Overhaul — Part B: Inline Expandable JSON (QListView)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `QTextEdit` in `LogViewer` with a `QListView` + `LogModel` + `LogDelegate` so that JSON log lines render as collapsible rows with a key/value table, while plain lines continue to render with syntax-color classification.

**Architecture:** `LogModel` (`QAbstractListModel`) stores `LogItem` objects and exposes them to the view. `LogDelegate` (`QStyledItemDelegate`) paints each row: plain text in one color, JSON in a collapsed summary or expanded key/value table. `LogViewer` swaps its `QTextEdit` for a `QListView` and delegates all data management to `LogModel`. `FilterSearchSidebar` is updated to use the new 3-tuple search match type.

**Prerequisites:** Plan A must be merged first — this plan depends on `TermRow.key` and the updated `_line_matches`.

**Tech Stack:** PyQt6 6.6+, Python 3.11+, pytest, ruff

---

## File Map

| File | Action | What changes |
|---|---|---|
| `ui.py` | Modify | Add `LogItem`, `LogModel`, `LogDelegate`, `_classify_line`, `_try_parse_json`, `_resolve_main_key`, `_MAIN_KEYS`. Rewrite `LogViewer`. Update `FilterSearchSidebar._scroll_to_match`. Remove `LogHighlighter`, `_LogTextEdit`, `_action_break`. |
| `tests/test_filter_logic.py` | Modify | Tests for `_try_parse_json`, `_classify_line` |

---

## Task 1: `_try_parse_json` + `_classify_line` + `_resolve_main_key`

These are pure functions — testable without any GUI. Add them at module level in `ui.py`, near the existing `_line_matches` and `_extract_json_keys` functions.

**Files:**
- Modify: `ui.py` (after `_extract_json_keys` at line ~1016)
- Modify: `tests/test_filter_logic.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_filter_logic.py`. Update `_import_logic` to also import the new functions:

```python
def _import_logic():
    import os as _os
    _os.environ.setdefault("DISPLAY", ":0")
    from ui import (
        TermRow, _line_matches, _extract_json_keys,
        _try_parse_json, _classify_line, _resolve_main_key,
    )
    return TermRow, _line_matches, _extract_json_keys, _try_parse_json, _classify_line, _resolve_main_key


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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python3 -m pytest tests/test_filter_logic.py -k "try_parse or classify or resolve_main" -v
```
Expected: FAIL (functions don't exist yet)

- [ ] **Step 3: Add the functions to `ui.py`**

Add after `_extract_json_keys` (line ~1016):

```python
# ── JSON parsing + line classification ─────────────────────────────────────────

def _try_parse_json(message: str) -> dict | None:
    """Try to parse message as a JSON object. Returns dict or None."""
    stripped = message.strip()
    if not stripped.startswith("{"):
        return None
    try:
        data = json.loads(stripped)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


_CLASSIFY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("error", re.compile(r"\b(CRITICAL|FATAL|ERROR|ERR)\b", re.IGNORECASE)),
    ("warn",  re.compile(r"\b(WARN(?:ING)?)\b",             re.IGNORECASE)),
    ("info",  re.compile(r"\bINFO\b",                       re.IGNORECASE)),
    ("debug", re.compile(r"\bDEBUG\b",                      re.IGNORECASE)),
    ("trace", re.compile(r"\bTRACE\b",                      re.IGNORECASE)),
]


def _classify_line(text: str) -> str:
    """Return severity level string for a log line."""
    for level, pattern in _CLASSIFY_PATTERNS:
        if pattern.search(text):
            return level
    return "plain"


_MAIN_KEYS = (
    "message", "msg", "error", "err", "data", "content", "text",
    "body", "log", "description", "details", "payload", "result", "output", "value",
)


def _resolve_main_key(data: dict) -> str | None:
    """Return the first priority key found in data, or None."""
    for k in _MAIN_KEYS:
        if k in data:
            return k
    return None
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/test_filter_logic.py -v
```
Expected: all pass

- [ ] **Step 5: Lint**

```bash
python3 -m ruff check . --fix
```

- [ ] **Step 6: Commit**

```bash
git add ui.py tests/test_filter_logic.py
git commit -m "feat: add _try_parse_json, _classify_line, _resolve_main_key helpers"
```

---

## Task 2: `LogItem` dataclass + `LogModel`

**Files:**
- Modify: `ui.py` (add after the new helper functions, before `LogHighlighter`)

- [ ] **Step 1: Add new Qt imports**

At the top of `ui.py`, add to the `from PyQt6.QtCore import` block:

```python
QAbstractListModel, QModelIndex,
```

Add to `from PyQt6.QtWidgets import`:
```python
QAbstractItemView, QListView,
```

- [ ] **Step 2: Add `LogItem` and custom roles**

Add after `_resolve_main_key`:

```python
# ── LogItem + LogModel ─────────────────────────────────────────────────────────

@dataclass
class LogItem:
    ts_ms: int
    message: str
    is_json: bool
    json_data: dict | None
    main_key: str | None
    expanded: bool = False
    visible: bool = True


_ITEM_ROLE     = Qt.ItemDataRole.UserRole + 1
_EXPANDED_ROLE = Qt.ItemDataRole.UserRole + 2
```

- [ ] **Step 3: Add `LogModel`**

```python
class LogModel(QAbstractListModel):
    rows_appended     = pyqtSignal()
    json_keys_updated = pyqtSignal(set)
    filter_applied    = pyqtSignal()

    _MAX_LINES = 10_000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[LogItem] = []
        self._visible: list[LogItem] = []   # references into _items
        self._json_keys: set[str] = set()
        self._current_filter_terms: list[TermRow] = []

    # ── QAbstractListModel interface ──────────────────────────────────────────

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self._visible)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._visible):
            return None
        item = self._visible[index.row()]
        if role == _ITEM_ROLE:
            return item
        if role == Qt.ItemDataRole.DisplayRole:
            return item.message
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if role == _EXPANDED_ROLE and index.isValid():
            item = self._visible[index.row()]
            item.expanded = bool(value)
            self.dataChanged.emit(index, index, [role])
            return True
        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    # ── Public API ────────────────────────────────────────────────────────────

    def append_events(self, events: list[tuple[int, str]]) -> None:
        if not events:
            return
        new_keys: set[str] = set()
        appended: list[LogItem] = []

        for ts_ms, message in events:
            json_data = _try_parse_json(message)
            main_key  = _resolve_main_key(json_data) if json_data else None
            item = LogItem(
                ts_ms=ts_ms,
                message=message,
                is_json=json_data is not None,
                json_data=json_data,
                main_key=main_key,
                visible=_line_matches(message, self._current_filter_terms),
            )
            self._items.append(item)
            appended.append(item)
            if json_data:
                new_keys |= set(json_data.keys())

        # Enforce MAX_LINES — bulk trim + reset if over limit
        if len(self._items) > self._MAX_LINES:
            self._items = self._items[-self._MAX_LINES:]
            self.beginResetModel()
            self._visible = [it for it in self._items if it.visible]
            self.endResetModel()
            self.rows_appended.emit()
        else:
            newly_visible = [it for it in appended if it.visible]
            if newly_visible:
                first = len(self._visible)
                self.beginInsertRows(QModelIndex(), first, first + len(newly_visible) - 1)
                self._visible.extend(newly_visible)
                self.endInsertRows()
                self.rows_appended.emit()

        if new_keys - self._json_keys:
            self._json_keys |= new_keys
            self.json_keys_updated.emit(self._json_keys.copy())

    def apply_filter(self, terms: list[TermRow]) -> None:
        self._current_filter_terms = terms
        self.beginResetModel()
        self._visible = []
        for item in self._items:
            item.visible = _line_matches(item.message, self._current_filter_terms)
            if item.visible:
                self._visible.append(item)
        self.endResetModel()
        self.filter_applied.emit()

    def clear(self) -> None:
        self.beginResetModel()
        self._items.clear()
        self._visible.clear()
        self._json_keys.clear()
        self.endResetModel()

    def get_json_keys(self) -> set[str]:
        return self._json_keys.copy()

    def visible_count(self) -> int:
        return len(self._visible)
```

- [ ] **Step 4: Write non-GUI tests for `LogModel`**

Add a new test file `tests/test_log_model.py`:

```python
"""Unit tests for LogModel — no GUI required."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("DISPLAY", ":0")


def _make_model():
    from ui import LogModel
    # LogModel needs a QApplication to exist for signal/slot machinery
    from PyQt6.QtWidgets import QApplication
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
    from ui import _ITEM_ROLE, _EXPANDED_ROLE
    model, _ = _make_model()
    model.append_events([(0, '{"message": "hi"}')])
    idx = model.index(0)
    item = model.data(idx, _ITEM_ROLE)
    assert item.expanded is False
    model.setData(idx, True, _EXPANDED_ROLE)
    assert item.expanded is True
```

- [ ] **Step 5: Run tests**

```bash
python3 -m pytest tests/test_log_model.py -v
```
Expected: all pass

- [ ] **Step 6: Lint**

```bash
python3 -m ruff check . --fix
```

- [ ] **Step 7: Commit**

```bash
git add ui.py tests/test_log_model.py
git commit -m "feat: add LogItem dataclass and LogModel QAbstractListModel"
```

---

## Task 3: `LogDelegate`

**Files:**
- Modify: `ui.py` (add after `LogModel`, before `LogHighlighter`)

- [ ] **Step 1: Add new Qt imports**

Add to `from PyQt6.QtCore import`:
```python
QEvent, QRect, QPoint,
```
Add to `from PyQt6.QtGui import`:
```python
QFontMetrics,
```
Add to `from PyQt6.QtWidgets import`:
```python
QStyledItemDelegate, QStyle,
```

- [ ] **Step 2: Add `LogDelegate`**

```python
# ── LogDelegate ────────────────────────────────────────────────────────────────

_ROW_H         = 22   # px — plain / JSON-collapsed row height
_TABLE_HEAD_H  = 22   # px — table header row height
_TABLE_ROW_H   = 18   # px — each key/value data row height
_TABLE_PAD_B   = 6    # px — padding below last table row
_ARROW_W       = 16   # px — width reserved for ▶/▼ toggle

_LEVEL_COLORS = {
    "error": C_ERR,
    "warn":  C_WARN,
    "info":  C_INFO,
    "debug": C_DEBUG,
    "trace": C_TRACE,
    "plain": "#d4d4d4",
}


class LogDelegate(QStyledItemDelegate):
    """Paints log rows. JSON rows are collapsible; plain rows use level colors."""

    def __init__(self, viewer, parent=None):
        super().__init__(parent)
        # viewer is the LogViewer — used to read show_timestamps flag
        self._viewer = viewer
        self._search_highlights: dict[int, list[tuple[int, int]]] = {}
        self._focused_match: tuple[int, int, int] | None = None  # (vis_idx, start, len)

    def set_search_highlights(
        self,
        highlights: dict[int, list[tuple[int, int]]],
    ) -> None:
        self._search_highlights = highlights

    def set_focused_match(self, vis_idx: int, char_start: int, char_len: int) -> None:
        self._focused_match = (vis_idx, char_start, char_len)

    # ── QStyledItemDelegate interface ─────────────────────────────────────────

    def sizeHint(self, option, index):
        item = index.data(_ITEM_ROLE)
        if item is None or not item.is_json or not item.expanded or not item.json_data:
            return QSize(option.rect.width(), _ROW_H)
        n = len(item.json_data)
        return QSize(
            option.rect.width(),
            _ROW_H + _TABLE_HEAD_H + _TABLE_ROW_H * n + _TABLE_PAD_B,
        )

    def paint(self, painter, option, index):
        item = index.data(_ITEM_ROLE)
        if item is None:
            return

        painter.save()
        painter.setClipRect(option.rect)

        # Selection / hover background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor("#1a3a6e55"))

        if item.is_json:
            self._paint_json(painter, option, index, item)
        else:
            self._paint_plain(painter, option, index, item)

        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonRelease:
            item = index.data(_ITEM_ROLE)
            if item and item.is_json and item.json_data:
                # Toggle only if click is within the arrow column
                if event.pos().x() <= option.rect.x() + _ARROW_W:
                    model.setData(index, not item.expanded, _EXPANDED_ROLE)
                    return True
        return False

    # ── Private paint helpers ─────────────────────────────────────────────────

    def _baseline(self, rect: QRect, fm: QFontMetrics, row_h: int = _ROW_H) -> int:
        """Return y baseline for text vertically centered in a row."""
        return rect.top() + (row_h - fm.height()) // 2 + fm.ascent()

    def _draw_segments(
        self,
        painter: QPainter,
        x: int,
        y: int,
        segments: list[tuple[str, str]],
        fm: QFontMetrics,
    ) -> int:
        """Draw (text, color) segments left-to-right. Returns x after last segment."""
        for text, color in segments:
            painter.setPen(QColor(color))
            painter.drawText(x, y, text)
            x += fm.horizontalAdvance(text)
        return x

    def _paint_plain(self, painter, option, index, item: LogItem) -> None:
        fm = painter.fontMetrics()
        y  = self._baseline(option.rect, fm)
        x  = option.rect.left() + 4

        color = _LEVEL_COLORS.get(_classify_line(item.message), "#d4d4d4")

        # Search highlight rect (drawn behind text)
        vis_idx = index.row()
        self._draw_search_bg(painter, option.rect, x, item.message, vis_idx, fm)

        # Timestamp prefix
        if self._viewer.show_timestamps and item.ts_ms:
            ts = datetime.fromtimestamp(item.ts_ms / 1000, tz=UTC).strftime("%H:%M:%S")
            x = self._draw_segments(painter, x, y, [(f"[{ts}]  ", C_TS)], fm)

        painter.setPen(QColor(color))
        painter.drawText(x, y, item.message)

    def _paint_json(self, painter, option, index, item: LogItem) -> None:
        fm   = painter.fontMetrics()
        rect = option.rect
        y    = self._baseline(rect, fm)
        x0   = rect.left() + 4

        # ▶/▼ toggle arrow
        arrow = "▼" if item.expanded else "▶"
        painter.setPen(QColor(C_MUTED))
        painter.drawText(x0, y, arrow)
        x = x0 + _ARROW_W

        # Timestamp
        if self._viewer.show_timestamps and item.ts_ms:
            ts = datetime.fromtimestamp(item.ts_ms / 1000, tz=UTC).strftime("%H:%M:%S")
            x = self._draw_segments(painter, x, y, [(f"[{ts}]  ", C_TS)], fm)

        # Main value (or first key=val if no main key)
        color = _LEVEL_COLORS.get(_classify_line(item.message), "#d4d4d4")
        if item.main_key and item.json_data:
            main_val = str(item.json_data[item.main_key])[:80]
            x = self._draw_segments(painter, x, y, [(main_val, color)], fm)
        elif item.json_data:
            # No standard key — show first two keys inline
            pairs = list(item.json_data.items())[:2]
            for k, v in pairs:
                seg = f"  {k}={str(v)[:30]}"
                x = self._draw_segments(painter, x, y, [(seg, C_MUTED)], fm)

        # Summary of remaining keys (collapsed only)
        if not item.expanded and item.json_data:
            shown_keys = {item.main_key} if item.main_key else set()
            if not item.main_key:
                shown_keys = {k for k, _ in list(item.json_data.items())[:2]}
            rest = [k for k in item.json_data if k not in shown_keys]
            if rest:
                shown_rest = rest[:2]
                for k in shown_rest:
                    seg = f"  · {k}={str(item.json_data[k])[:20]}"
                    x = self._draw_segments(painter, x, y, [(seg, C_MUTED)], fm)
                remaining = len(rest) - len(shown_rest)
                if remaining > 0:
                    x = self._draw_segments(painter, x, y, [(f"  +{remaining}", C_MUTED)], fm)

        # Expanded table
        if item.expanded and item.json_data:
            self._paint_table(painter, rect, item, fm)

    def _paint_table(self, painter, rect: QRect, item: LogItem, fm: QFontMetrics) -> None:
        key_col_w = 110
        x_key = rect.left() + _ARROW_W + 4
        x_val = x_key + key_col_w + 8

        # Table header
        header_y = rect.top() + _ROW_H
        painter.fillRect(
            QRect(rect.left(), header_y, rect.width(), _TABLE_HEAD_H),
            QColor("#161616"),
        )
        header_base = header_y + ((_TABLE_HEAD_H - fm.height()) // 2) + fm.ascent()
        painter.setPen(QColor(C_MUTED))
        painter.drawText(x_key, header_base, "key")
        painter.drawText(x_val, header_base, "value")

        # Data rows
        for i, (k, v) in enumerate(item.json_data.items()):
            row_top  = header_y + _TABLE_HEAD_H + i * _TABLE_ROW_H
            row_base = row_top + ((_TABLE_ROW_H - fm.height()) // 2) + fm.ascent()

            # Alternating row background
            if i % 2 == 0:
                painter.fillRect(QRect(rect.left(), row_top, rect.width(), _TABLE_ROW_H),
                                 QColor("#111111"))

            painter.setPen(QColor(C_TRACE))
            painter.drawText(x_key, row_base, str(k)[:20])

            val_color = self._value_color(v)
            painter.setPen(QColor(val_color))
            painter.drawText(x_val, row_base, str(v)[:80])

    def _value_color(self, v) -> str:
        if isinstance(v, bool):
            return C_WARN
        if isinstance(v, (int, float)):
            return C_DEBUG
        if v is None:
            return C_MUTED
        return "#d4d4d4"

    def _draw_search_bg(
        self,
        painter: QPainter,
        row_rect: QRect,
        text_x: int,
        text: str,
        vis_idx: int,
        fm: QFontMetrics,
    ) -> None:
        """Draw yellow background rects behind search match characters."""
        highlights = self._search_highlights.get(vis_idx, [])
        if not highlights:
            return
        y = row_rect.top() + 2
        h = row_rect.height() - 4
        for char_start, char_len in highlights:
            prefix_w = fm.horizontalAdvance(text[:char_start])
            match_w  = fm.horizontalAdvance(text[char_start:char_start + char_len])
            color = "#ffd54f66"
            focused = self._focused_match
            if focused and focused[0] == vis_idx and focused[1] == char_start:
                color = "#ffd54faa"
            painter.fillRect(QRect(text_x + prefix_w, y, match_w, h), QColor(color))
```

- [ ] **Step 3: Run existing tests**

```bash
python3 -m pytest -v
```
Expected: all pass (delegate is not tested directly — smoke test comes in Task 5)

- [ ] **Step 4: Lint**

```bash
python3 -m ruff check . --fix
```

- [ ] **Step 5: Commit**

```bash
git add ui.py
git commit -m "feat: add LogDelegate with plain/JSON-collapsed/JSON-expanded paint"
```

---

## Task 4: `LogViewer` — swap `QTextEdit` for `QListView`

This is the main refactor. `LogViewer` keeps its public API (`append_events`, `apply_filter`, `apply_search`, `clear`, `get_json_keys`, all signals) but its internals move to `LogModel` + `LogDelegate` + `QListView`.

**Files:**
- Modify: `ui.py:1082-1351` (`LogViewer` class)

- [ ] **Step 1: Rewrite `LogViewer.__init__` and `_build_ui`**

Replace the `LogViewer` class body. Keep the same class-level signals and `_MAX_LINES`. Remove `_raw_events`, `_filtering`, `_pending_during_filter` instance variables. Add `_model`, `_delegate`, `_list_view`, `_search_highlights`.

```python
class LogViewer(QWidget):
    stop_requested    = pyqtSignal()
    json_keys_updated = pyqtSignal(set)
    lines_appended    = pyqtSignal()
    filter_applied    = pyqtSignal()

    _MAX_LINES = 10_000

    def __init__(self, source_type: str = "cloudwatch", parent=None):
        super().__init__(parent)
        self._source_type = source_type
        self._search_highlights: dict[int, list[tuple[int, int]]] = {}

        self._model = LogModel(self)
        self._model.json_keys_updated.connect(self.json_keys_updated)
        self._model.rows_appended.connect(self._on_rows_appended)
        self._model.filter_applied.connect(self.filter_applied)
        self._model._MAX_LINES = self._MAX_LINES

        self._build_ui()

        _key = id(self)
        i18n.register(_key, self.retranslate)
        self.destroyed.connect(lambda _=None, k=_key: i18n.unregister(k))

    @property
    def show_timestamps(self) -> bool:
        return self.timestamps_cb.isChecked()

    def _on_rows_appended(self) -> None:
        if self.autoscroll_cb.isChecked():
            self._list_view.scrollToBottom()
        self.lines_appended.emit()
        self.line_badge.setText(i18n.tr("viewer_lines", n=self._model.visible_count()))

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Toolbar ──
        toolbar = QWidget()
        toolbar.setFixedHeight(48)
        toolbar.setStyleSheet(
            f"background: {C_TOOLBAR}; border-bottom: 1px solid {C_DIVIDER};"
        )
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(12, 0, 12, 0)
        tb.setSpacing(8)

        src_color = _SOURCE_COLORS.get(self._source_type, C_TEXT)
        self._source_badge = QLabel(self._source_type.upper())
        self._source_badge.setStyleSheet(
            f"background: {C_SEL_BG}; color: {src_color}; border-radius: 10px;"
            "padding: 2px 10px; font-size: 11px; font-weight: bold; border: none;"
        )

        self.title_label = QLabel("—")
        self.title_label.setStyleSheet(
            f"font-weight: bold; color: {C_TEXT}; background: transparent; border: none;"
        )

        self.line_badge = QLabel(i18n.tr("viewer_lines", n=0))
        self.line_badge.setStyleSheet(
            f"background: {C_CARD}; color: {C_MUTED}; border-radius: 10px;"
            "padding: 2px 10px; font-size: 11px; border: none;"
        )

        self.autoscroll_cb = QCheckBox()
        self.autoscroll_cb.setChecked(True)

        self.timestamps_cb = QCheckBox()
        self.timestamps_cb.setChecked(True)
        self.timestamps_cb.stateChanged.connect(
            lambda _: self._list_view.viewport().update()
        )

        self.clear_btn = QPushButton()
        self.clear_btn.setObjectName("danger")
        self.clear_btn.setFixedHeight(32)
        self.clear_btn.clicked.connect(self.clear)

        self.stop_btn = QPushButton()
        self.stop_btn.setFixedHeight(32)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_requested)

        tb.addWidget(self._source_badge)
        tb.addWidget(self.title_label)
        tb.addStretch()
        tb.addWidget(self.line_badge)
        tb.addWidget(self.autoscroll_cb)
        tb.addWidget(self.timestamps_cb)
        tb.addWidget(self.clear_btn)
        tb.addWidget(self.stop_btn)
        layout.addWidget(toolbar)

        # ── List view ──
        self._delegate = LogDelegate(viewer=self)
        self._list_view = QListView()
        self._list_view.setModel(self._model)
        self._list_view.setItemDelegate(self._delegate)
        self._list_view.setUniformItemSizes(False)
        self._list_view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._list_view.setStyleSheet(
            f"QListView {{ background: {C_RAIL}; border: none; border-radius: 0; }}"
            f"QListView::item:selected {{ background: #1a3a6e33; }}"
        )
        font = self._list_view.font()
        font.setFamily("JetBrains Mono, Fira Code, Cascadia Code, monospace")
        font.setPointSize(9)
        self._list_view.setFont(font)
        layout.addWidget(self._list_view)

        self.retranslate()
```

- [ ] **Step 2: Rewrite `LogViewer` public API methods**

Replace `append_events`, `apply_filter`, `apply_search`, `clear`, `get_json_keys`, and add `set_title`, `copy`, `scroll_to_search_match`:

```python
    def retranslate(self) -> None:
        src_key = f"src_{self._source_type}"
        self._source_badge.setText(i18n.tr(src_key))
        self.autoscroll_cb.setText(i18n.tr("viewer_autoscroll"))
        self.timestamps_cb.setText(i18n.tr("viewer_timestamps"))
        self.clear_btn.setText(i18n.tr("viewer_clear"))
        self.stop_btn.setText(i18n.tr("viewer_stop"))
        self.line_badge.setText(i18n.tr("viewer_lines", n=self._model.visible_count()))

    def set_title(self, text: str) -> None:
        self.title_label.setText(text)

    def append_events(self, events: list[tuple[int, str]]) -> None:
        self._model.append_events(events)

    def apply_filter(self, terms: list[TermRow]) -> None:
        self._model.apply_filter(terms)
        self.line_badge.setText(i18n.tr("viewer_lines", n=self._model.visible_count()))

    def apply_search(self, terms: list[TermRow]) -> list[tuple[int, int, int]]:
        """Return (visible_row_idx, char_start, char_len) for every match."""
        self._search_highlights.clear()
        active = [t for t in terms if t.text.strip() and not t.key]
        if not active:
            self._delegate.set_search_highlights({})
            self._list_view.viewport().update()
            return []

        results: list[tuple[int, int, int]] = []
        highlights: dict[int, list[tuple[int, int]]] = {}

        for vis_idx in range(self._model.rowCount()):
            item = self._model.data(self._model.index(vis_idx), _ITEM_ROLE)
            if item is None:
                continue
            for term in active:
                pattern = re.compile(re.escape(term.text), re.IGNORECASE)
                for m in pattern.finditer(item.message):
                    results.append((vis_idx, m.start(), m.end() - m.start()))
                    highlights.setdefault(vis_idx, []).append(
                        (m.start(), m.end() - m.start())
                    )

        self._search_highlights = highlights
        self._delegate.set_search_highlights(highlights)
        self._list_view.viewport().update()
        return sorted(results, key=lambda t: (t[0], t[1]))

    def scroll_to_search_match(self, vis_idx: int, char_start: int, char_len: int) -> None:
        idx = self._model.index(vis_idx)
        self._list_view.scrollTo(idx, QAbstractItemView.ScrollHint.EnsureVisible)
        self._delegate.set_focused_match(vis_idx, char_start, char_len)
        self._list_view.viewport().update()

    def clear(self) -> None:
        self._model.clear()
        self._search_highlights.clear()
        self._delegate.set_search_highlights({})
        self.line_badge.setText(i18n.tr("viewer_lines", n=0))

    def get_json_keys(self) -> set[str]:
        return self._model.get_json_keys()

    def copy(self) -> None:
        """Copy selected rows' text to clipboard."""
        indexes = self._list_view.selectedIndexes()
        if not indexes:
            return
        texts = []
        for idx in sorted(indexes, key=lambda i: i.row()):
            item = self._model.data(idx, _ITEM_ROLE)
            if item:
                texts.append(item.message)
        QApplication.clipboard().setText("\n".join(texts))
```

- [ ] **Step 3: Run all tests**

```bash
python3 -m pytest -v
```
Expected: all pass

- [ ] **Step 4: Lint**

```bash
python3 -m ruff check . --fix
```

- [ ] **Step 5: Commit**

```bash
git add ui.py
git commit -m "feat: replace QTextEdit with QListView+LogModel+LogDelegate in LogViewer"
```

---

## Task 5: `FilterSearchSidebar` — update search navigation

**Files:**
- Modify: `ui.py` (`FilterSearchSidebar` class, lines ~1427+)

- [ ] **Step 1: Update `_search_matches` type and `_scroll_to_match`**

In `FilterSearchSidebar.__init__`, change the type annotation:
```python
self._search_matches: list[tuple[int, int, int]] = []  # was list[tuple[int, int]]
```

Replace `_scroll_to_match`:
```python
def _scroll_to_match(self, index: int) -> None:
    if self._active_viewer is None or not self._search_matches:
        return
    vis_idx, char_start, char_len = self._search_matches[index]
    self._active_viewer.scroll_to_search_match(vis_idx, char_start, char_len)
```

- [ ] **Step 2: Run all tests**

```bash
python3 -m pytest -v
```
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add ui.py
git commit -m "feat: update FilterSearchSidebar to use 3-tuple search matches"
```

---

## Task 6: Cleanup

Remove now-dead code: `LogHighlighter`, `_LogTextEdit`, the Enter-key separator, `Edit → Break`.

**Files:**
- Modify: `ui.py`

- [ ] **Step 1: Remove `LogHighlighter` class**

Delete the entire `LogHighlighter` class (lines ~1021–1059) and its import `QSyntaxHighlighter` from the `from PyQt6.QtGui import` block.

- [ ] **Step 2: Remove `_LogTextEdit` class**

Delete the entire `_LogTextEdit` class (lines ~1071–1079).

- [ ] **Step 3: Remove `_insert_separator` from `LogViewer`**

Delete the `_insert_separator` method (~lines 1334–1347). It's no longer callable.

- [ ] **Step 4: Remove `Edit → Break` from `MainWindow`**

In `_build_menubar`, delete:
```python
self._act_break = QAction(self)
self._act_break.setShortcut(QKeySequence("Ctrl+Return"))
self._act_break.triggered.connect(self._action_break)
self._menu_edit.addAction(self._act_break)
```

Delete `_action_break` method:
```python
def _action_break(self) -> None:
    ...
```

In `_retranslate_menubar`, delete:
```python
self._act_break.setText(i18n.tr("action_break"))
```

- [ ] **Step 5: Update `_action_copy` in `MainWindow`**

The old implementation called `viewer.text_edit.copy()`. Replace with:
```python
def _action_copy(self) -> None:
    viewer = self._active_viewer()
    if viewer:
        viewer.copy()
```

- [ ] **Step 6: Remove unused imports**

Remove from `from PyQt6.QtGui import`:
- `QSyntaxHighlighter` (if still present after step 1)
- `QTextCharFormat` (used only in old `LogViewer.append_events` and `LogHighlighter`)
- `QTextCursor` (used only in old `LogViewer` methods)

Remove from `from PyQt6.QtCore import`:
- `QRectF` (check if used elsewhere)

Remove from top-level imports (if no longer used after cleanup):
- `deque` from `collections`

Run ruff to catch any remaining unused imports automatically.

- [ ] **Step 7: Remove `action_break` i18n key**

In `i18n.py`, remove the `"action_break"` key from both the `"en"` and `"fr"` translation dicts.

- [ ] **Step 8: Run all tests**

```bash
python3 -m pytest -v
```
Expected: all pass

- [ ] **Step 9: Lint**

```bash
python3 -m ruff check . --fix
```

- [ ] **Step 10: Commit**

```bash
git add ui.py i18n.py
git commit -m "chore: remove LogHighlighter, _LogTextEdit, Edit→Break (replaced by QListView delegate)"
```

---

## Task 7: Final integration

- [ ] **Step 1: Run full test suite**

```bash
python3 -m pytest -v
```
Expected: all pass

- [ ] **Step 2: Lint**

```bash
python3 -m ruff check .
```
Expected: no issues

- [ ] **Step 3: Push**

```bash
git push origin master
```

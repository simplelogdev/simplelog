# Filter & Search Sidebar — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a global 280 px right sidebar to MainWindow with multi-term filter (AND/OR, hides non-matching lines), multi-term search (AND/OR, highlights + navigation), and a JSON key chip panel — replacing the per-viewer search bar.

**Architecture:** All UI lives in `ui.py`. The sidebar is a fixed-width `QWidget` added to the root `QHBoxLayout` after `self._splitter`. `LogViewer` gains a `_raw_events` deque buffer, signals (`json_keys_updated`, `lines_appended`, `filter_applied`), and `apply_filter`/`apply_search` methods. Pure logic (`TermRow`, `_line_matches`, `_extract_json_keys`) lives at module level for testability.

**Tech Stack:** PyQt6 6.6+, Python 3.11+, pytest, ruff

---

## File Map

| File | Action | What changes |
|---|---|---|
| `i18n.py` | Modify | Add 12 sidebar keys, remove `viewer_search_ph` + `action_paste`, update `help_content` |
| `ui.py` | Modify | Add `TermRow`, `_line_matches`, `_extract_json_keys`, extend `LogHighlighter`, extend `LogViewer`, add `_TermRowWidget` + `FilterSearchSidebar` classes, update `MainWindow` |
| `tests/test_i18n.py` | Modify | Add tests for new sidebar keys |
| `tests/test_filter_logic.py` | Create | Unit tests for `_line_matches` and `_extract_json_keys` |

No new source files — `ui.py` is the established pattern for all UI classes in this project.

---

## Task 1: i18n — add sidebar keys, remove dead keys, update help text

**Files:**
- Modify: `i18n.py`
- Modify: `tests/test_i18n.py`

- [ ] **Step 1: Write failing tests for new sidebar keys**

Add to `tests/test_i18n.py`:

```python
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
    i18n.set_locale("en")
    assert i18n.tr("action_paste") == "action_paste"
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_i18n.py::test_sidebar_search_key_en tests/test_i18n.py::test_viewer_search_ph_removed -v
```
Expected: FAIL

- [ ] **Step 3: Update `i18n.py` — EN block**

In the `"en"` dict, **remove** these two keys:
```python
"action_paste":          "Paste",
"viewer_search_ph":      "Search…  Ctrl+F",
```

**Add** after the `"viewer_lines"` key:
```python
# ── Sidebar ───────────────────────────────────────────────────
"sidebar_search":        "Search",
"sidebar_filter":        "Filter",
"sidebar_json_keys":     "JSON Keys",
"sidebar_add_and":       "+ AND",
"sidebar_add_or":        "+ OR",
"sidebar_prev":          "▲ Prev",
"sidebar_next":          "▼ Next",
"sidebar_hits":          "{n:,} hits",
"sidebar_no_hits":       "No results",
"sidebar_term_ph":       "Term…",
"sidebar_live_filter":   "Live",
"sidebar_json_ph":       "Detected keys…",
```

**Update** `help_content` EN — replace the KEYBOARD SHORTCUTS section:
```python
"KEYBOARD SHORTCUTS\n"
"  Ctrl+F            Focus sidebar search\n"
"  Ctrl+Shift+F      Toggle sidebar\n"
"\n"
```

- [ ] **Step 4: Update `i18n.py` — FR block**

In the `"fr"` dict, **remove** the same two keys:
```python
"action_paste":          "Coller",
"viewer_search_ph":      "Rechercher…  Ctrl+F",
```

**Add** after `"viewer_lines"`:
```python
# ── Sidebar ───────────────────────────────────────────────────
"sidebar_search":        "Recherche",
"sidebar_filter":        "Filtrer",
"sidebar_json_keys":     "Clés JSON",
"sidebar_add_and":       "+ ET",
"sidebar_add_or":        "+ OU",
"sidebar_prev":          "▲ Préc",
"sidebar_next":          "▼ Suiv",
"sidebar_hits":          "{n:,} résultats",
"sidebar_no_hits":       "Aucun résultat",
"sidebar_term_ph":       "Terme…",
"sidebar_live_filter":   "En direct",
"sidebar_json_ph":       "Clés détectées…",
```

**Update** `help_content` FR — replace the RACCOURCIS CLAVIER section:
```python
"RACCOURCIS CLAVIER\n"
"  Ctrl+F            Activer la recherche dans la sidebar\n"
"  Ctrl+Shift+F      Afficher / masquer la sidebar\n"
"\n"
```

- [ ] **Step 5: Run tests**

```
pytest tests/test_i18n.py -v
```
Expected: all pass

- [ ] **Step 6: Lint**

```
ruff check i18n.py tests/test_i18n.py
```

- [ ] **Step 7: Commit**

```bash
git add i18n.py tests/test_i18n.py
git commit -m "feat: add sidebar i18n keys, remove action_paste + viewer_search_ph"
```

---

## Task 2: Pure logic — TermRow, _line_matches, _extract_json_keys

**Files:**
- Modify: `ui.py` (module level, before `LogHighlighter`)
- Create: `tests/test_filter_logic.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_filter_logic.py`:

```python
"""Unit tests for pure filter/search logic in ui.py."""
import sys
import os

# Prevent PyQt6 import during testing — we only need the module-level functions
# We import them via a shim after adding the project root to sys.path.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def _import_logic():
    """Import only after ensuring no display is needed."""
    # Set a dummy display env if not set (Linux CI without $DISPLAY)
    import os as _os
    _os.environ.setdefault("DISPLAY", ":0")
    # These functions are module-level in ui.py and do NOT create any widgets
    from ui import TermRow, _line_matches, _extract_json_keys
    return TermRow, _line_matches, _extract_json_keys


# ── TermRow ───────────────────────────────────────────────────────────────────

def test_term_row_first_has_empty_operator():
    TermRow, _, _ = _import_logic()
    t = TermRow(text="foo", operator="")
    assert t.operator == ""


# ── _line_matches ─────────────────────────────────────────────────────────────

def test_no_terms_matches_everything():
    _, _line_matches, _ = _import_logic()
    assert _line_matches("anything here", []) is True


def test_single_term_match():
    TermRow, _line_matches, _ = _import_logic()
    terms = [TermRow("error", "")]
    assert _line_matches("ERROR: disk full", terms) is True


def test_single_term_no_match():
    TermRow, _line_matches, _ = _import_logic()
    terms = [TermRow("error", "")]
    assert _line_matches("INFO: all good", terms) is False


def test_case_insensitive():
    TermRow, _line_matches, _ = _import_logic()
    terms = [TermRow("ERROR", "")]
    assert _line_matches("error: something", terms) is True


def test_and_both_match():
    TermRow, _line_matches, _ = _import_logic()
    terms = [TermRow("error", ""), TermRow("disk", "AND")]
    assert _line_matches("ERROR: disk full", terms) is True


def test_and_second_missing():
    TermRow, _line_matches, _ = _import_logic()
    terms = [TermRow("error", ""), TermRow("disk", "AND")]
    assert _line_matches("ERROR: memory full", terms) is False


def test_or_first_matches():
    TermRow, _line_matches, _ = _import_logic()
    terms = [TermRow("error", ""), TermRow("warn", "OR")]
    assert _line_matches("ERROR: something", terms) is True


def test_or_second_matches():
    TermRow, _line_matches, _ = _import_logic()
    terms = [TermRow("error", ""), TermRow("warn", "OR")]
    assert _line_matches("WARN: low memory", terms) is True


def test_or_neither_matches():
    TermRow, _line_matches, _ = _import_logic()
    terms = [TermRow("error", ""), TermRow("warn", "OR")]
    assert _line_matches("INFO: all good", terms) is False


def test_empty_term_text_matches_all():
    TermRow, _line_matches, _ = _import_logic()
    terms = [TermRow("", "")]  # empty text = match all
    assert _line_matches("anything", terms) is True


# ── _extract_json_keys ────────────────────────────────────────────────────────

def test_pure_json_object():
    _, _, _extract_json_keys = _import_logic()
    keys = _extract_json_keys('{"level": "ERROR", "msg": "fail", "userId": 42}')
    assert keys == {"level", "msg", "userId"}


def test_non_json_line_returns_empty_or_partial():
    _, _, _extract_json_keys = _import_logic()
    keys = _extract_json_keys("plain log line with no JSON")
    assert isinstance(keys, set)  # may be empty or have false positives, that's OK


def test_json_embedded_in_line():
    _, _, _extract_json_keys = _import_logic()
    line = '2024-01-01 ERROR {"requestId": "abc", "status": 500}'
    keys = _extract_json_keys(line)
    assert "requestId" in keys
    assert "status" in keys


def test_invalid_json_uses_fallback_regex():
    _, _, _extract_json_keys = _import_logic()
    # Not valid JSON but has "key": patterns
    line = '{"userId": 1, broken}'
    keys = _extract_json_keys(line)
    assert "userId" in keys
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_filter_logic.py -v
```
Expected: FAIL (TermRow, _line_matches, _extract_json_keys not in ui.py yet)

- [ ] **Step 3: Add imports to `ui.py`**

At the top of `ui.py`, add:
```python
import json
from collections import deque
from dataclasses import dataclass
```

Also add `QTimer` to the PyQt6.QtCore import block:
```python
from PyQt6.QtCore import (
    QRectF,
    QSize,
    Qt,
    QTimer,
    QUrl,
    pyqtSignal,
)
```

- [ ] **Step 4: Add TermRow and logic functions to `ui.py`**

Insert right before the line `class LogHighlighter(QSyntaxHighlighter):` (currently around line 985):

```python
# ── Filter / search data model ─────────────────────────────────────────────────

@dataclass
class TermRow:
    text: str
    operator: str  # "AND" | "OR" | "" — empty string for the first term (ignored)


def _line_matches(line: str, terms: list[TermRow]) -> bool:
    """Return True if *line* satisfies the AND/OR chain of *terms* (case-insensitive)."""
    if not terms:
        return True
    low = line.lower()
    result = terms[0].text.lower() in low
    for term in terms[1:]:
        hit = term.text.lower() in low
        result = (result and hit) if term.operator == "AND" else (result or hit)
    return result


def _extract_json_keys(line: str) -> set[str]:
    """Extract top-level JSON keys from *line*. Best-effort; never raises."""
    try:
        obj = json.loads(line)
        if isinstance(obj, dict):
            return set(obj.keys())
    except (json.JSONDecodeError, ValueError):
        pass
    # Fallback: regex for "key": patterns (handles JSON embedded in a longer line)
    return set(re.findall(r'"([\w_-]+)"\s*:', line))
```

- [ ] **Step 5: Run tests**

```
pytest tests/test_filter_logic.py -v
```
Expected: all pass

- [ ] **Step 6: Lint**

```
ruff check ui.py tests/test_filter_logic.py
```

- [ ] **Step 7: Commit**

```bash
git add ui.py tests/test_filter_logic.py
git commit -m "feat: add TermRow, _line_matches, _extract_json_keys"
```

---

## Task 3: LogHighlighter — instance-level search rules

**Files:**
- Modify: `ui.py` — `LogHighlighter` class (currently around lines 985–1004)

No new tests (requires QTextDocument; outside the no-PyQt6 test constraint).

- [ ] **Step 1: Update `LogHighlighter`**

Replace the entire `LogHighlighter` class:

```python
class LogHighlighter(QSyntaxHighlighter):
    RULES = [
        (re.compile(r"\b(CRITICAL|FATAL)\b",  re.IGNORECASE), C_ERR,   True),
        (re.compile(r"\b(ERROR|ERR)\b",        re.IGNORECASE), C_ERR,   False),
        (re.compile(r"\b(WARN(?:ING)?)\b",     re.IGNORECASE), C_WARN,  False),
        (re.compile(r"\b(INFO)\b",             re.IGNORECASE), C_INFO,  False),
        (re.compile(r"\b(DEBUG)\b",            re.IGNORECASE), C_DEBUG, False),
        (re.compile(r"\b(TRACE)\b",            re.IGNORECASE), C_TRACE, False),
        (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"), C_TS,  False),
        (re.compile(r'"[\w_-]+"(?=\s*:)'),     C_TRACE, False),
    ]

    def __init__(self, document):
        super().__init__(document)
        self._search_rules: list[re.Pattern[str]] = []

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for pattern, color, bold in self.RULES:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if bold:
                fmt.setFontWeight(700)
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)
        # Search highlights: background only, so severity colours are preserved
        if self._search_rules:
            search_fmt = QTextCharFormat()
            search_fmt.setBackground(QColor("#3a3a00"))
            for pattern in self._search_rules:
                for m in pattern.finditer(text):
                    self.setFormat(m.start(), m.end() - m.start(), search_fmt)

    def set_search_terms(self, terms: list[TermRow]) -> None:
        self._search_rules = [
            re.compile(re.escape(t.text), re.IGNORECASE)
            for t in terms
            if t.text.strip()
        ]
        self.rehighlight()
```

- [ ] **Step 2: Run existing tests to confirm nothing broken**

```
pytest -v
```
Expected: all 84+ pass

- [ ] **Step 3: Lint**

```
ruff check ui.py
```

- [ ] **Step 4: Commit**

```bash
git add ui.py
git commit -m "feat: add instance search rules to LogHighlighter"
```

---

## Task 4: LogViewer — remove search bar, add buffer + signals + filter + search

**Files:**
- Modify: `ui.py` — `LogViewer` class (lines ~1027–1210)

This task has many changes. Work through them in sub-steps.

### 4a: Remove search bar and paste action

- [ ] **Step 1: Remove `search_input` from `LogViewer._build_ui`**

Locate `LogViewer._build_ui` (around line 1041). Remove:
- `self.search_input = QLineEdit()` and the two lines following it
- `tb.addWidget(self.search_input)` in the toolbar addWidget block
- The entire `# Ctrl+F shortcut` block (2 lines: `sc = QShortcut(...)` and `sc.activated.connect(...)`)

- [ ] **Step 2: Remove `viewer_search_ph` from `LogViewer.retranslate`**

Remove the line:
```python
self.search_input.setPlaceholderText(i18n.tr("viewer_search_ph"))
```

- [ ] **Step 3: Remove `_search_next` method from `LogViewer`**

Delete the entire `_search_next` method (lines ~1201–1209):
```python
def _search_next(self):
    text = self.search_input.text()
    ...
```

- [ ] **Step 4: Remove Edit → Paste from `MainWindow._build_menubar`**

In `_build_menubar` (around line 1276), remove these 4 lines:
```python
self._act_paste = QAction(self)
self._act_paste.setShortcut(QKeySequence("Ctrl+V"))
self._act_paste.triggered.connect(self._action_paste)
self._menu_edit.addAction(self._act_paste)
```

In `_retranslate_menubar` (around line 1339), remove:
```python
self._act_paste.setText(i18n.tr("action_paste"))
```

Delete the `_action_paste` method (around line 1413–1418):
```python
def _action_paste(self) -> None:
    ...
```

- [ ] **Step 5: Run all tests**

```
pytest -v
```
Expected: all pass (no tests relied on the removed code)

- [ ] **Step 6: Launch the app manually to confirm no crash**

```
python3 main.py
```
Expected: app opens, no search bar visible in viewer toolbar, Edit menu has no Paste item.

- [ ] **Step 7: Commit**

```bash
git add ui.py
git commit -m "feat: remove per-viewer search bar and Edit>Paste menu item"
```

### 4b: Add buffer, signals, and modified append_events

- [ ] **Step 1: Add signals to `LogViewer` class body**

Right after `stop_requested = pyqtSignal()` at the top of `LogViewer`, add:

```python
json_keys_updated = pyqtSignal(set)
lines_appended    = pyqtSignal()
filter_applied    = pyqtSignal()
```

- [ ] **Step 2: Add instance state to `LogViewer.__init__`**

In `LogViewer.__init__`, after `self._build_ui()`, add:

```python
self._raw_events: deque[tuple[int, str]] = deque(maxlen=self._MAX_LINES)
self._json_keys: set[str] = set()
self._filtering: bool = False
self._pending_during_filter: list[tuple[int, str]] = []
self._current_filter_terms: list[TermRow] = []
```

- [ ] **Step 3: Replace `append_events` with the new version**

Replace the entire `append_events` method with:

```python
def append_events(self, events: list[tuple[int, str]]):
    # 1. Buffer all raw events (deque caps at _MAX_LINES automatically)
    for ev in events:
        self._raw_events.append(ev)

    # 2. Detect JSON keys (always, regardless of filter state)
    new_keys: set[str] = set()
    for _, message in events:
        new_keys |= _extract_json_keys(message)
    if new_keys - self._json_keys:
        self._json_keys |= new_keys
        self.json_keys_updated.emit(self._json_keys.copy())

    # 3. If apply_filter is running, buffer events for later display
    if self._filtering:
        self._pending_during_filter.extend(events)
        return

    # 4. Write matching events to the QTextEdit display
    cursor = self.text_edit.textCursor()
    show_ts = self.timestamps_cb.isChecked()
    wrote_any = False

    for ts_ms, message in events:
        if not _line_matches(message, self._current_filter_terms):
            continue

        # Trim oldest display line if at the display limit
        if self._line_count >= self._MAX_LINES:
            c2 = self.text_edit.textCursor()
            c2.movePosition(QTextCursor.MoveOperation.Start)
            c2.movePosition(
                QTextCursor.MoveOperation.Down,
                QTextCursor.MoveMode.KeepAnchor,
            )
            c2.removeSelectedText()
            self._line_count -= 1

        cursor.movePosition(QTextCursor.MoveOperation.End)
        if show_ts and ts_ms:
            ts_str = datetime.fromtimestamp(
                ts_ms / 1000, tz=UTC
            ).strftime("%H:%M:%S")
            line = f"[{ts_str}]  {message}"
        else:
            line = message

        default_fmt = QTextCharFormat()
        default_fmt.setForeground(QColor("#d4d4d4"))
        if self._line_count > 0:
            cursor.insertText("\n", default_fmt)
        cursor.insertText(line, default_fmt)
        self._line_count += 1
        wrote_any = True

    self.line_badge.setText(i18n.tr("viewer_lines", n=self._line_count))
    if self.autoscroll_cb.isChecked():
        sb = self.text_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

    if wrote_any:
        self.lines_appended.emit()
```

- [ ] **Step 4: Add `apply_filter`, `get_json_keys`, `apply_search` methods**

Add after `append_events`:

```python
def apply_filter(self, terms: list[TermRow]) -> None:
    """Re-render the display from _raw_events through *terms*."""
    self._current_filter_terms = terms
    self._filtering = True
    self._pending_during_filter.clear()

    self.text_edit.clear()
    self._line_count = 0

    cursor = self.text_edit.textCursor()
    show_ts = self.timestamps_cb.isChecked()

    for ts_ms, message in self._raw_events:
        if not _line_matches(message, terms):
            continue

        if show_ts and ts_ms:
            ts_str = datetime.fromtimestamp(
                ts_ms / 1000, tz=UTC
            ).strftime("%H:%M:%S")
            line = f"[{ts_str}]  {message}"
        else:
            line = message

        default_fmt = QTextCharFormat()
        default_fmt.setForeground(QColor("#d4d4d4"))
        if self._line_count > 0:
            cursor.insertText("\n", default_fmt)
        cursor.insertText(line, default_fmt)
        self._line_count += 1

        # UI-freeze mitigation: yield to the event loop every 500 lines
        if self._line_count % 500 == 0:
            QApplication.processEvents()

    self.line_badge.setText(i18n.tr("viewer_lines", n=self._line_count))
    self._filtering = False

    # Flush events that arrived during filtering
    if self._pending_during_filter:
        pending = self._pending_during_filter[:]
        self._pending_during_filter.clear()
        self.append_events(pending)

    if self.autoscroll_cb.isChecked():
        sb = self.text_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

    self.filter_applied.emit()


def get_json_keys(self) -> set[str]:
    return self._json_keys.copy()


def apply_search(self, terms: list[TermRow]) -> list[tuple[int, int]]:
    """Highlight search terms and return sorted (position, length) match list."""
    self._highlighter.set_search_terms(terms)
    matches: list[tuple[int, int]] = []
    active = [t for t in terms if t.text.strip()]
    if not active:
        return matches
    text = self.text_edit.toPlainText()
    for term in active:
        pattern = re.compile(re.escape(term.text), re.IGNORECASE)
        for m in pattern.finditer(text):
            matches.append((m.start(), m.end() - m.start()))
    matches.sort(key=lambda x: x[0])
    return matches
```

- [ ] **Step 5: Run all tests**

```
pytest -v
```
Expected: all pass

- [ ] **Step 6: Smoke test — open a log file and confirm live filtering works**

```
python3 main.py /var/log/syslog   # or any available log file
```
Expected: viewer shows log content as before (no filter active = all lines visible).

- [ ] **Step 7: Commit**

```bash
git add ui.py
git commit -m "feat: LogViewer gains raw buffer, json key detection, apply_filter, apply_search"
```

---

## Task 5: FilterSearchSidebar widget

**Files:**
- Modify: `ui.py` — add two new classes (`_TermRowWidget`, `FilterSearchSidebar`) before `MainWindow`

Insert the full block right before `class MainWindow(QMainWindow):` (currently around line 1212).

### 5a: _TermRowWidget

- [ ] **Step 1: Add `_TermRowWidget` class**

```python
# ── Sidebar helper: one term input row ────────────────────────────────────────

class _TermRowWidget(QWidget):
    """A single filter/search term row: [op toggle] [input] [×]."""

    changed          = pyqtSignal()
    remove_requested = pyqtSignal()

    def __init__(self, operator: str = "", placeholder: str = "", parent=None):
        super().__init__(parent)
        self._operator = operator  # "" for the first row

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        # Operator toggle button (AND ↔ OR), hidden for first row
        self._op_btn = QPushButton(operator or "AND")
        self._op_btn.setFixedSize(42, 24)
        self._op_btn.setVisible(bool(operator))
        self._op_btn.setStyleSheet(
            f"QPushButton {{ background: {C_SEL_BG}; color: {C_ACCENT}; "
            f"border-radius: 4px; font-size: 10px; font-weight: bold; border: none; }}"
            f"QPushButton:hover {{ background: {C_DIVIDER}; }}"
        )
        self._op_btn.clicked.connect(self._toggle_operator)
        row.addWidget(self._op_btn)

        # Invisible spacer to align inputs when no op button
        self._op_spacer = QWidget()
        self._op_spacer.setFixedSize(42, 24)
        self._op_spacer.setVisible(not bool(operator))
        row.addWidget(self._op_spacer)

        # Term text input
        self._input = QLineEdit()
        self._input.setPlaceholderText(placeholder)
        self._input.setStyleSheet(
            f"background: {C_CARD}; color: {C_TEXT}; border: 1px solid {C_DIVIDER}; "
            "border-radius: 4px; padding: 2px 6px; font-size: 12px;"
        )
        self._input.textChanged.connect(self.changed)
        row.addWidget(self._input, stretch=1)

        # Remove button
        self._rm_btn = QPushButton("×")
        self._rm_btn.setFixedSize(24, 24)
        self._rm_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C_MUTED}; "
            "border: none; font-size: 16px; }}"
            f"QPushButton:hover {{ color: {C_ERR}; }}"
        )
        self._rm_btn.clicked.connect(self.remove_requested)
        row.addWidget(self._rm_btn)

    def _toggle_operator(self) -> None:
        self._operator = "OR" if self._operator == "AND" else "AND"
        self._op_btn.setText(self._operator)
        self.changed.emit()

    def to_term_row(self) -> TermRow:
        return TermRow(text=self._input.text(), operator=self._operator)

    def set_placeholder(self, text: str) -> None:
        self._input.setPlaceholderText(text)

    def focus_input(self) -> None:
        self._input.setFocus()

    def set_text(self, text: str) -> None:
        self._input.setText(text)
```

### 5b: FilterSearchSidebar

- [ ] **Step 2: Add `FilterSearchSidebar` class**

```python
# ── Right sidebar: filter + search + JSON keys ─────────────────────────────────

class FilterSearchSidebar(QWidget):
    """Global right sidebar. Call set_active_viewer() when the active tab changes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self.setStyleSheet(
            f"FilterSearchSidebar {{ background: {C_RAIL}; "
            f"border-left: 1px solid {C_DIVIDER}; }}"
        )

        self._active_viewer: LogViewer | None = None
        self._search_matches: list[tuple[int, int]] = []
        self._search_match_index: int = -1
        self._search_term_widgets: list[_TermRowWidget] = []
        self._filter_term_widgets: list[_TermRowWidget] = []
        self._section_labels: list[QLabel] = []

        # Debounce timers
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(150)
        self._filter_timer.timeout.connect(self._apply_filter_now)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(150)
        self._search_timer.timeout.connect(self._apply_search_now)

        self._lines_timer = QTimer(self)
        self._lines_timer.setSingleShot(True)
        self._lines_timer.setInterval(300)
        self._lines_timer.timeout.connect(self._apply_search_now)

        self._build_ui()

        _key = id(self)
        i18n.register(_key, self.retranslate)
        self.destroyed.connect(lambda _=None, k=_key: i18n.unregister(k))

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(0)

        # ── SEARCH ──
        layout.addWidget(self._make_section_header("sidebar_search"))
        self._search_rows_widget = QWidget()
        self._search_rows_widget.setStyleSheet("background: transparent;")
        self._search_rows_layout = QVBoxLayout(self._search_rows_widget)
        self._search_rows_layout.setContentsMargins(12, 0, 12, 0)
        self._search_rows_layout.setSpacing(4)
        layout.addWidget(self._search_rows_widget)
        self._add_search_row("")   # initial empty row

        add_search = QHBoxLayout()
        add_search.setContentsMargins(12, 4, 12, 0)
        self._btn_add_search_and = QPushButton()
        self._btn_add_search_and.clicked.connect(lambda: self._add_search_row("AND"))
        self._btn_add_search_or  = QPushButton()
        self._btn_add_search_or.clicked.connect(lambda: self._add_search_row("OR"))
        for btn in (self._btn_add_search_and, self._btn_add_search_or):
            btn.setFixedHeight(24)
            btn.setStyleSheet(self._add_btn_style())
        add_search.addWidget(self._btn_add_search_and)
        add_search.addWidget(self._btn_add_search_or)
        add_search.addStretch()
        layout.addLayout(add_search)

        nav = QHBoxLayout()
        nav.setContentsMargins(12, 6, 12, 8)
        self._btn_prev = QPushButton()
        self._btn_next = QPushButton()
        self._lbl_hits = QLabel()
        self._lbl_hits.setStyleSheet(f"color: {C_MUTED}; font-size: 11px;")
        for btn in (self._btn_prev, self._btn_next):
            btn.setFixedHeight(28)
            btn.setStyleSheet(self._nav_btn_style())
        self._btn_prev.clicked.connect(self._search_prev)
        self._btn_next.clicked.connect(self._search_next_match)
        nav.addWidget(self._btn_prev)
        nav.addWidget(self._btn_next)
        nav.addWidget(self._lbl_hits)
        nav.addStretch()
        layout.addLayout(nav)

        layout.addWidget(self._make_divider())

        # ── FILTER ──
        layout.addWidget(self._make_section_header("sidebar_filter"))
        self._filter_rows_widget = QWidget()
        self._filter_rows_widget.setStyleSheet("background: transparent;")
        self._filter_rows_layout = QVBoxLayout(self._filter_rows_widget)
        self._filter_rows_layout.setContentsMargins(12, 0, 12, 0)
        self._filter_rows_layout.setSpacing(4)
        layout.addWidget(self._filter_rows_widget)
        self._add_filter_row("")   # initial empty row

        add_filter = QHBoxLayout()
        add_filter.setContentsMargins(12, 4, 12, 0)
        self._btn_add_filter_and = QPushButton()
        self._btn_add_filter_and.clicked.connect(lambda: self._add_filter_row("AND"))
        self._btn_add_filter_or  = QPushButton()
        self._btn_add_filter_or.clicked.connect(lambda: self._add_filter_row("OR"))
        for btn in (self._btn_add_filter_and, self._btn_add_filter_or):
            btn.setFixedHeight(24)
            btn.setStyleSheet(self._add_btn_style())
        add_filter.addWidget(self._btn_add_filter_and)
        add_filter.addWidget(self._btn_add_filter_or)
        add_filter.addStretch()
        layout.addLayout(add_filter)

        live_row = QHBoxLayout()
        live_row.setContentsMargins(12, 6, 12, 8)
        self._cb_live = QCheckBox()
        self._cb_live.setChecked(True)
        self._cb_live.setStyleSheet(f"color: {C_MUTED}; font-size: 11px;")
        live_row.addWidget(self._cb_live)
        live_row.addStretch()
        layout.addLayout(live_row)

        layout.addWidget(self._make_divider())

        # ── JSON KEYS ──
        layout.addWidget(self._make_section_header("sidebar_json_keys"))
        self._json_container = QWidget()
        self._json_container.setStyleSheet("background: transparent;")
        self._json_layout = QVBoxLayout(self._json_container)
        self._json_layout.setContentsMargins(12, 0, 12, 8)
        self._json_layout.setSpacing(4)
        self._lbl_json_ph = QLabel()
        self._lbl_json_ph.setStyleSheet(f"color: {C_MUTED}; font-size: 11px;")
        self._json_layout.addWidget(self._lbl_json_ph)
        layout.addWidget(self._json_container)

        layout.addStretch()

        scroll.setWidget(inner)
        outer.addWidget(scroll)

        # Ctrl+F: focus sidebar search (window-wide shortcut)
        sc = QShortcut(QKeySequence("Ctrl+F"), self)
        sc.setContext(Qt.ShortcutContext.WindowShortcut)
        sc.activated.connect(self._focus_first_search)

        self.retranslate()

    def _make_section_header(self, key: str) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        h = QHBoxLayout(w)
        h.setContentsMargins(12, 12, 12, 4)
        lbl = QLabel()
        lbl.setStyleSheet(
            f"color: {C_MUTED}; font-size: 10px; font-weight: bold; "
            "text-transform: uppercase; background: transparent;"
        )
        lbl.setProperty("i18n_key", key)
        self._section_labels.append(lbl)
        h.addWidget(lbl)
        h.addStretch()
        return w

    def _make_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {C_DIVIDER};")
        return line

    def _add_btn_style(self) -> str:
        return (
            f"QPushButton {{ background: {C_SEL_BG}; color: {C_MUTED}; "
            f"border-radius: 4px; font-size: 11px; padding: 0 8px; border: none; }}"
            f"QPushButton:hover {{ color: {C_TEXT}; }}"
        )

    def _nav_btn_style(self) -> str:
        return (
            f"QPushButton {{ background: {C_SEL_BG}; color: {C_TEXT}; "
            f"border-radius: 4px; font-size: 12px; padding: 0 10px; border: none; }}"
            f"QPushButton:hover {{ background: {C_DIVIDER}; }}"
        )

    # ── Term row management ───────────────────────────────────────────────────

    def _add_search_row(self, operator: str) -> None:
        row = _TermRowWidget(operator, parent=self)
        row.changed.connect(self._on_search_changed)
        row.remove_requested.connect(lambda r=row: self._remove_search_row(r))
        self._search_term_widgets.append(row)
        self._search_rows_layout.addWidget(row)
        row.set_placeholder(i18n.tr("sidebar_term_ph"))

    def _remove_search_row(self, row: _TermRowWidget) -> None:
        if len(self._search_term_widgets) == 1:
            return  # always keep at least one row
        self._search_term_widgets.remove(row)
        self._search_rows_layout.removeWidget(row)
        row.deleteLater()
        self._on_search_changed()

    def _add_filter_row(self, operator: str) -> None:
        row = _TermRowWidget(operator, parent=self)
        row.changed.connect(self._on_filter_changed)
        row.remove_requested.connect(lambda r=row: self._remove_filter_row(r))
        self._filter_term_widgets.append(row)
        self._filter_rows_layout.addWidget(row)
        row.set_placeholder(i18n.tr("sidebar_term_ph"))

    def _remove_filter_row(self, row: _TermRowWidget) -> None:
        if len(self._filter_term_widgets) == 1:
            return
        self._filter_term_widgets.remove(row)
        self._filter_rows_layout.removeWidget(row)
        row.deleteLater()
        self._on_filter_changed()

    # ── Signal handlers ───────────────────────────────────────────────────────

    def _on_search_changed(self) -> None:
        self._search_timer.start()

    def _on_filter_changed(self) -> None:
        if self._cb_live.isChecked():
            self._filter_timer.start()

    def _on_json_keys_updated(self, keys: set) -> None:
        self._rebuild_json_chips(keys)

    def _on_lines_appended(self) -> None:
        self._lines_timer.start()   # debounced search re-scan

    # ── Active viewer management ──────────────────────────────────────────────

    def set_active_viewer(self, viewer: LogViewer | None) -> None:
        if self._active_viewer is not None:
            self._active_viewer.json_keys_updated.disconnect(self._on_json_keys_updated)
            self._active_viewer.lines_appended.disconnect(self._on_lines_appended)
            self._active_viewer.filter_applied.disconnect(self._refresh_search)
        self._active_viewer = viewer
        if viewer is not None:
            viewer.json_keys_updated.connect(self._on_json_keys_updated)
            viewer.lines_appended.connect(self._on_lines_appended)
            viewer.filter_applied.connect(self._refresh_search)
            self._on_json_keys_updated(viewer.get_json_keys())
            viewer.apply_filter(self._current_filter_terms())
            # _refresh_search is triggered by filter_applied signal

    def _current_filter_terms(self) -> list[TermRow]:
        return [w.to_term_row() for w in self._filter_term_widgets]

    def _current_search_terms(self) -> list[TermRow]:
        return [w.to_term_row() for w in self._search_term_widgets]

    # ── Apply filter / search ─────────────────────────────────────────────────

    def _apply_filter_now(self) -> None:
        if self._active_viewer:
            self._active_viewer.apply_filter(self._current_filter_terms())

    def _apply_search_now(self) -> None:
        self._refresh_search()

    def _refresh_search(self) -> None:
        if self._active_viewer is None:
            self._search_matches = []
            self._search_match_index = -1
            self._update_hits_label()
            return
        terms = self._current_search_terms()
        self._search_matches = self._active_viewer.apply_search(terms)
        self._search_match_index = 0 if self._search_matches else -1
        self._update_hits_label()
        if self._search_matches:
            self._scroll_to_match(0)

    def _search_prev(self) -> None:
        if not self._search_matches:
            return
        self._search_match_index = (self._search_match_index - 1) % len(self._search_matches)
        self._scroll_to_match(self._search_match_index)
        self._update_hits_label()

    def _search_next_match(self) -> None:
        if not self._search_matches:
            return
        self._search_match_index = (self._search_match_index + 1) % len(self._search_matches)
        self._scroll_to_match(self._search_match_index)
        self._update_hits_label()

    def _scroll_to_match(self, index: int) -> None:
        if self._active_viewer is None or not self._search_matches:
            return
        pos, length = self._search_matches[index]
        cursor = self._active_viewer.text_edit.textCursor()
        cursor.setPosition(pos)
        cursor.setPosition(pos + length, QTextCursor.MoveMode.KeepAnchor)
        self._active_viewer.text_edit.setTextCursor(cursor)

    def _update_hits_label(self) -> None:
        n = len(self._search_matches)
        if n == 0:
            self._lbl_hits.setText(i18n.tr("sidebar_no_hits"))
        else:
            self._lbl_hits.setText(i18n.tr("sidebar_hits", n=n))

    # ── JSON chips ────────────────────────────────────────────────────────────

    def _rebuild_json_chips(self, keys: set) -> None:
        # Clear existing chips, but do NOT delete the placeholder label widget
        while self._json_layout.count():
            item = self._json_layout.takeAt(0)
            w = item.widget()
            if w and w is not self._lbl_json_ph:
                w.deleteLater()

        sorted_keys = sorted(keys)[:50]  # cap at 50
        if not sorted_keys:
            self._json_layout.addWidget(self._lbl_json_ph)
            return

        for key in sorted_keys:
            btn = QPushButton(key)
            btn.setFixedHeight(24)
            btn.setStyleSheet(
                f"QPushButton {{ background: {C_SEL_BG}; color: {C_TRACE}; "
                f"border-radius: 4px; font-size: 11px; padding: 0 8px; border: none; "
                f"text-align: left; }}"
                f"QPushButton:hover {{ background: {C_DIVIDER}; }}"
            )
            btn.clicked.connect(lambda checked=False, k=key: self._add_filter_from_key(k))
            self._json_layout.addWidget(btn)

    def _add_filter_from_key(self, key: str) -> None:
        # If the last filter row is empty, fill it; otherwise append a new AND row
        last = self._filter_term_widgets[-1] if self._filter_term_widgets else None
        if last and last.to_term_row().text == "":
            last.set_text(key)
        else:
            self._add_filter_row("AND")
            self._filter_term_widgets[-1].set_text(key)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _focus_first_search(self) -> None:
        if self._search_term_widgets:
            self._search_term_widgets[0].focus_input()
        self.show()

    def retranslate(self) -> None:
        for lbl in self._section_labels:
            key = lbl.property("i18n_key")
            if key:
                lbl.setText(i18n.tr(key))
        self._btn_add_search_and.setText(i18n.tr("sidebar_add_and"))
        self._btn_add_search_or.setText(i18n.tr("sidebar_add_or"))
        self._btn_prev.setText(i18n.tr("sidebar_prev"))
        self._btn_next.setText(i18n.tr("sidebar_next"))
        self._btn_add_filter_and.setText(i18n.tr("sidebar_add_and"))
        self._btn_add_filter_or.setText(i18n.tr("sidebar_add_or"))
        self._cb_live.setText(i18n.tr("sidebar_live_filter"))
        self._lbl_json_ph.setText(i18n.tr("sidebar_json_ph"))
        for w in self._search_term_widgets + self._filter_term_widgets:
            w.set_placeholder(i18n.tr("sidebar_term_ph"))
        self._update_hits_label()
```

- [ ] **Step 3: Run all tests**

```
pytest -v
```
Expected: all pass

- [ ] **Step 4: Lint**

```
ruff check ui.py
```

- [ ] **Step 5: Commit**

```bash
git add ui.py
git commit -m "feat: add _TermRowWidget and FilterSearchSidebar"
```

---

## Task 6: MainWindow — wire the sidebar

**Files:**
- Modify: `ui.py` — `MainWindow` class

- [ ] **Step 1: Add sidebar to `_build_ui`**

In `MainWindow._build_ui`, after `root.addWidget(self._splitter, stretch=1)` (around line 1267), add:

```python
self._sidebar = FilterSearchSidebar(self)
root.addWidget(self._sidebar)
```

- [ ] **Step 2: Add `Ctrl+Shift+F` toggle shortcut**

In `_build_ui`, after adding the sidebar:

```python
sc_toggle = QShortcut(QKeySequence("Ctrl+Shift+F"), self)
sc_toggle.activated.connect(lambda: self._sidebar.setVisible(not self._sidebar.isVisible()))
```

- [ ] **Step 3: Add `_on_active_viewer_changed` method**

Add after `_active_viewer`:

```python
def _on_active_viewer_changed(self, pane: QTabWidget) -> None:
    """Called whenever focus moves to a different pane or tab."""
    self._active_pane = pane
    widget = pane.currentWidget()
    viewer = widget if isinstance(widget, LogViewer) else None
    self._sidebar.set_active_viewer(viewer)
```

- [ ] **Step 4: Update `_set_active_pane`**

Replace:
```python
def _set_active_pane(self, pane: QTabWidget):
    self._active_pane = pane
```
With:
```python
def _set_active_pane(self, pane: QTabWidget):
    self._on_active_viewer_changed(pane)
```

- [ ] **Step 5: Verify `_make_pane` — no code change needed**

`_set_active_pane` now delegates to `_on_active_viewer_changed` (Step 4). The existing `tabs.currentChanged.connect(lambda _, t=tabs: self._set_active_pane(t))` in `_make_pane` therefore already notifies the sidebar on tab switches. **No code change required in this step.** Just confirm the lambda is present.

- [ ] **Step 6: Update `_add_tab` — notify sidebar after adding**

In `_add_tab`, after `self._active_pane = target`, add:

```python
widget = target.currentWidget()
if isinstance(widget, LogViewer):
    self._sidebar.set_active_viewer(widget)
```

- [ ] **Step 7: Update `_close_tab` — disconnect sidebar when active viewer is closed**

Replace the existing `_close_tab` with:

```python
def _close_tab(self, index: int, tabs: QTabWidget):
    viewer = tabs.widget(index)

    # Unconditionally disconnect sidebar from this viewer before removing it.
    # set_active_viewer guards against double-disconnect via its None check.
    self._sidebar.set_active_viewer(None)

    self._stop_viewer(viewer)
    tabs.removeTab(index)

    # Re-point sidebar to new active tab if one remains
    if tabs is self._active_pane and tabs.count() > 0:
        new_widget = tabs.currentWidget()
        if isinstance(new_widget, LogViewer):
            self._sidebar.set_active_viewer(new_widget)

    # Remove empty secondary panes (keep at least one pane)
    if tabs.count() == 0 and tabs in self._panes and len(self._panes) > 1:
        self._panes.remove(tabs)
        tabs.setParent(None)  # type: ignore[call-overload]
        if self._active_pane is tabs:
            self._active_pane = self._panes[0]
```

- [ ] **Step 8: Run all tests**

```
pytest -v
```
Expected: all pass

- [ ] **Step 9: Full manual smoke test**

```
python3 main.py /path/to/app.log /path/to/error.log --split vertical
```

Verify:
- Sidebar visible on right, 280 px wide
- Ctrl+F focuses first search input in sidebar
- Ctrl+Shift+F toggles sidebar visibility
- Typing in the filter field hides non-matching lines live
- Typing in the search field highlights matches in yellow
- ▲ Prev / ▼ Next navigate between matches
- Clicking a JSON key chip adds it as a filter term
- Switching tabs/panes updates the sidebar's JSON keys panel
- Closing a tab doesn't crash the app

- [ ] **Step 10: Lint**

```
ruff check ui.py
```

- [ ] **Step 11: Commit**

```bash
git add ui.py
git commit -m "feat: wire FilterSearchSidebar into MainWindow"
```

---

## Task 7: Final integration tests and cleanup

- [ ] **Step 1: Run full test suite**

```
pytest -v
```
Expected: all pass

- [ ] **Step 2: Verify i18n completeness**

```python
# Quick check: all sidebar keys present in both locales
python3 -c "
import i18n
keys = ['sidebar_search','sidebar_filter','sidebar_json_keys',
        'sidebar_add_and','sidebar_add_or','sidebar_prev','sidebar_next',
        'sidebar_hits','sidebar_no_hits','sidebar_term_ph',
        'sidebar_live_filter','sidebar_json_ph']
for loc in ['en','fr']:
    i18n.set_locale(loc)
    for k in keys:
        v = i18n.tr(k)
        assert v != k, f'Missing key {k} in {loc}'
print('All sidebar i18n keys present in EN and FR')
"
```

- [ ] **Step 3: Verify removed keys are gone**

```python
python3 -c "
import i18n
for loc in ['en','fr']:
    i18n.set_locale(loc)
    assert i18n.tr('viewer_search_ph') == 'viewer_search_ph', f'viewer_search_ph still in {loc}'
    assert i18n.tr('action_paste') == 'action_paste', f'action_paste still in {loc}'
print('Removed keys confirmed absent')
"
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: filter/search sidebar complete"
```

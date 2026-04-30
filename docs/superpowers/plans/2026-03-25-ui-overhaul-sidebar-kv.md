# UI Overhaul — Part A: Sidebar Redesign & key=value Filter

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the right sidebar to IDE-style (VS Code/JetBrains) and add a dedicated key=value row type to the filter, allowing JSON key-based filtering (e.g. `skills = toto`).

**Architecture:** All changes are in `ui.py` (pure style + logic, no widget architecture change). `TermRow` gains a `key` field; `_line_matches` handles key-based JSON matching; `_TermRowWidget` gains a `mode="kv"` variant with two inputs; `FilterSearchSidebar` gets new styles, collapsible sections, and the `+ key=val` button. This plan is a prerequisite for Plan B (QListView).

**Tech Stack:** PyQt6 6.6+, Python 3.11+, pytest, ruff

---

## File Map

| File | Action | What changes |
|---|---|---|
| `ui.py` | Modify | `TermRow` key field, `_line_matches` KV logic, `_TermRowWidget` kv mode, `FilterSearchSidebar` visual overhaul |
| `tests/test_filter_logic.py` | Modify | Tests for KV matching |

---

## Task 1: TermRow + `_line_matches` — key=value support

**Files:**
- Modify: `ui.py:990-1004`
- Modify: `tests/test_filter_logic.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_filter_logic.py`. The tests will fail because `TermRow` has no `key` field yet — constructing `TermRow(text=..., operator=..., key=...)` will raise `TypeError`:

```python
def _import_logic():
    import os as _os
    _os.environ.setdefault("DISPLAY", ":0")
    from ui import TermRow, _line_matches, _extract_json_keys
    return TermRow, _line_matches, _extract_json_keys


# ── KV matching ───────────────────────────────────────────────────────────────

def test_kv_match_exact():
    TermRow, _line_matches, _ = _import_logic()
    terms = [TermRow(text="toto", operator="", key="skills")]
    assert _line_matches('{"skills": "toto", "source": "api"}', terms) is True


def test_kv_match_case_insensitive():
    TermRow, _line_matches, _ = _import_logic()
    terms = [TermRow(text="TOTO", operator="", key="skills")]
    assert _line_matches('{"skills": "toto"}', terms) is True


def test_kv_match_partial():
    TermRow, _line_matches, _ = _import_logic()
    terms = [TermRow(text="tot", operator="", key="skills")]
    assert _line_matches('{"skills": "toto"}', terms) is True


def test_kv_no_match_wrong_value():
    TermRow, _line_matches, _ = _import_logic()
    terms = [TermRow(text="other", operator="", key="skills")]
    assert _line_matches('{"skills": "toto"}', terms) is False


def test_kv_no_match_not_json():
    TermRow, _line_matches, _ = _import_logic()
    terms = [TermRow(text="toto", operator="", key="skills")]
    assert _line_matches("plain text line with toto", terms) is False


def test_kv_no_match_missing_key():
    TermRow, _line_matches, _ = _import_logic()
    terms = [TermRow(text="toto", operator="", key="skills")]
    assert _line_matches('{"other": "toto"}', terms) is False


def test_kv_empty_text_matches_key_presence():
    TermRow, _line_matches, _ = _import_logic()
    terms = [TermRow(text="", operator="", key="skills")]
    assert _line_matches('{"skills": "anything"}', terms) is True
    assert not _line_matches('{"other": "val"}', terms)


def test_kv_mixed_with_text_term_and():
    TermRow, _line_matches, _ = _import_logic()
    terms = [
        TermRow(text="error", operator=""),
        TermRow(text="toto", operator="AND", key="skills"),
    ]
    assert _line_matches('error: {"skills": "toto"}', terms) is True
    assert not _line_matches('info: {"skills": "toto"}', terms)


def test_kv_numeric_value():
    TermRow, _line_matches, _ = _import_logic()
    terms = [TermRow(text="401", operator="", key="status")]
    assert _line_matches('{"status": 401}', terms) is True
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python3 -m pytest tests/test_filter_logic.py -k "kv" -v
```
Expected: FAIL (TermRow has no `key` field yet)

- [ ] **Step 3: Add `key` field to `TermRow`**

In `ui.py` at line 989, update `TermRow`:

```python
@dataclass
class TermRow:
    text: str
    operator: str  # "AND" | "OR" | "" — empty string for the first term (ignored)
    key: str = ""  # non-empty → JSON key=value match mode
```

- [ ] **Step 4: Update `_line_matches` for KV terms**

Replace the current `_line_matches` function (line 995–1004):

```python
def _line_matches(line: str, terms: list[TermRow]) -> bool:
    """Return True if *line* satisfies the AND/OR chain of *terms* (case-insensitive)."""
    if not terms:
        return True

    def _term_hit(term: TermRow) -> bool:
        if not term.key:
            # Plain text match
            return term.text.lower() in line.lower()
        # Key=value match: parse line as JSON, check data[key] contains text
        try:
            data = json.loads(line.strip())
        except (json.JSONDecodeError, ValueError):
            return False
        if not isinstance(data, dict) or term.key not in data:
            return False
        if term.text == "":
            return True  # key presence check
        return term.text.lower() in str(data[term.key]).lower()

    result = _term_hit(terms[0])
    for term in terms[1:]:
        hit = _term_hit(term)
        result = (result and hit) if term.operator == "AND" else (result or hit)
    return result
```

- [ ] **Step 5: Run tests**

```bash
python3 -m pytest tests/test_filter_logic.py -v
```
Expected: all pass

- [ ] **Step 6: Lint**

```bash
python3 -m ruff check . --fix
```

- [ ] **Step 7: Commit**

```bash
git add ui.py tests/test_filter_logic.py
git commit -m "feat: add TermRow.key field and KV matching to _line_matches"
```

---

## Task 2: `_TermRowWidget` — KV mode

**Files:**
- Modify: `ui.py:1354-1423`

- [ ] **Step 1: Verify all callers of `_TermRowWidget`**

Before changing the constructor, confirm every call site in `ui.py`. The current signature is `(operator, placeholder="", parent=None)`. Search:

```bash
grep -n "_TermRowWidget(" ui.py
```

Expected: all calls use keyword `parent=` and do not pass `placeholder` positionally. If any pass a positional second argument (a string placeholder), update those callers to use `set_placeholder()` after construction instead. The new signature `(operator, mode="text", parent=None)` drops `placeholder` — any positional string would silently become `mode` and cause a layout bug.

- [ ] **Step 2: Add `mode` parameter and KV layout**

Replace the `_TermRowWidget.__init__` with the version below. The key change: when `mode="kv"`, show two inputs (key + value) instead of one, connected by an `=` label.

```python
class _TermRowWidget(QWidget):
    """A single filter/search term row: [op toggle] [input(s)] [×]."""

    changed          = pyqtSignal()
    remove_requested = pyqtSignal()

    def __init__(self, operator: str = "", mode: str = "text", parent=None):
        super().__init__(parent)
        self._operator = operator
        self._mode = mode  # "text" | "kv"

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        # Operator toggle (AND ↔ OR), hidden for first row
        self._op_btn = QPushButton(operator or "AND")
        self._op_btn.setFixedSize(36, 20)
        self._op_btn.setVisible(bool(operator))
        self._op_btn.setStyleSheet(
            f"QPushButton {{ background: #78d9ec1a; color: {C_TS}; "
            f"border-radius: 3px; font-size: 9px; font-weight: bold; border: none; }}"
            f"QPushButton:hover {{ background: #78d9ec33; }}"
        )
        self._op_btn.clicked.connect(self._toggle_operator)
        row.addWidget(self._op_btn)

        # Spacer when no op button (aligns inputs across rows)
        self._op_spacer = QWidget()
        self._op_spacer.setFixedSize(36, 20)
        self._op_spacer.setVisible(not bool(operator))
        row.addWidget(self._op_spacer)

        _input_style = (
            f"background: transparent; color: {C_TEXT}; border: none; "
            "padding: 0 4px; font-size: 11px;"
        )

        if mode == "kv":
            self._key_input = QLineEdit()
            self._key_input.setFixedWidth(60)
            self._key_input.setStyleSheet(
                f"background: transparent; color: {C_TRACE}; border: none; "
                "padding: 0 4px; font-size: 11px;"
            )
            self._key_input.textChanged.connect(self.changed)
            row.addWidget(self._key_input)

            eq_lbl = QLabel("=")
            eq_lbl.setStyleSheet(f"color: {C_MUTED}; font-size: 11px; background: transparent;")
            eq_lbl.setFixedWidth(10)
            row.addWidget(eq_lbl)

            self._val_input = QLineEdit()
            self._val_input.setStyleSheet(_input_style)
            self._val_input.textChanged.connect(self.changed)
            row.addWidget(self._val_input, stretch=1)

            # Alias for common API (set_placeholder, focus_input target val)
            self._input = self._val_input
        else:
            self._input = QLineEdit()
            self._input.setStyleSheet(_input_style)
            self._input.textChanged.connect(self.changed)
            row.addWidget(self._input, stretch=1)

        # Remove button
        self._rm_btn = QPushButton("×")
        self._rm_btn.setFixedSize(20, 20)
        self._rm_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C_MUTED}; "
            "border: none; font-size: 14px; padding: 0; }}"
            f"QPushButton:hover {{ color: {C_ERR}; }}"
        )
        self._rm_btn.clicked.connect(self.remove_requested)
        row.addWidget(self._rm_btn)

    def _toggle_operator(self) -> None:
        self._operator = "OR" if self._operator == "AND" else "AND"
        self._op_btn.setText(self._operator)
        self.changed.emit()

    def to_term_row(self) -> TermRow:
        if self._mode == "kv":
            return TermRow(
                text=self._val_input.text(),
                operator=self._operator,
                key=self._key_input.text(),
            )
        return TermRow(text=self._input.text(), operator=self._operator)

    def set_placeholder(self, text: str) -> None:
        self._input.setPlaceholderText(text)

    def focus_input(self) -> None:
        self._input.setFocus()

    def focus_value_input(self) -> None:
        """Focus the value input (kv mode) or the regular input (text mode)."""
        self._input.setFocus()

    def set_text(self, text: str) -> None:
        """In kv mode, sets the key field. In text mode, sets the single input."""
        if self._mode == "kv":
            self._key_input.setText(text)
        else:
            self._input.setText(text)
```

- [ ] **Step 2: Run existing tests**

```bash
python3 -m pytest -v
```
Expected: all pass (no API change externally)

- [ ] **Step 3: Lint**

```bash
python3 -m ruff check . --fix
```

- [ ] **Step 4: Commit**

```bash
git add ui.py
git commit -m "feat: add mode='kv' to _TermRowWidget for key=value filter rows"
```

---

## Task 3: FilterSearchSidebar — KV integration

> **Note on task ordering:** Task 3 patches the *existing* `_build_ui` to add the `+ key=val` button. Task 4 then **replaces `_build_ui` entirely** with the new IDE-style layout — `_build_filter_content` in Task 4 already includes the kv button. There is no double-creation: Task 4 supersedes the Task 3 insertion. The purpose of Task 3 is to validate the KV row logic works end-to-end before doing the full visual overhaul.

**Files:**
- Modify: `ui.py:1427-1805` (FilterSearchSidebar)

- [ ] **Step 1: Update `_add_filter_row` signature**

Change the `_add_filter_row` method to accept `mode` and `prefill_key`:

```python
def _add_filter_row(self, operator: str, mode: str = "text", prefill_key: str = "") -> None:
    row = _TermRowWidget(operator, mode=mode, parent=self)
    row.changed.connect(self._on_filter_changed)
    row.remove_requested.connect(lambda r=row: self._remove_filter_row(r))
    self._filter_term_widgets.append(row)
    self._filter_rows_layout.addWidget(row)
    row.set_placeholder(i18n.tr("sidebar_term_ph"))
    if prefill_key:
        row.set_text(prefill_key)
```

- [ ] **Step 2: Add `+ key=val` button to filter section**

In `_build_ui`, after the `add_filter` layout setup (where `_btn_add_filter_and` and `_btn_add_filter_or` are created), add:

```python
self._btn_add_filter_kv = QPushButton()
self._btn_add_filter_kv.clicked.connect(lambda: self._add_filter_row("AND", mode="kv"))
self._btn_add_filter_kv.setFixedHeight(24)
self._btn_add_filter_kv.setStyleSheet(self._add_btn_style())
add_filter.addWidget(self._btn_add_filter_kv)
```

And in `retranslate()`, add:
```python
self._btn_add_filter_kv.setText("+ key=val")
```

- [ ] **Step 3: Update `_add_filter_from_key` to create a KV row**

Replace the existing method:

```python
def _add_filter_from_key(self, key: str) -> None:
    """Called when a JSON key chip is clicked. Creates a KV row pre-filled with the key."""
    self._add_filter_row("AND", mode="kv", prefill_key=key)
    self._filter_term_widgets[-1].focus_value_input()
    if self._cb_live.isChecked():
        self._filter_timer.start()
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add ui.py
git commit -m "feat: add + key=val button to filter sidebar and KV chip-click integration"
```

---

## Task 4: Sidebar visual redesign (IDE style)

**Files:**
- Modify: `ui.py:1427-1805` (FilterSearchSidebar._build_ui, styles)

This task replaces the flat dark sidebar style with the style-C IDE design: collapsible sections with clickable headers, term rows grouped in a unified block, compact nav controls, chip pills without fill.

- [ ] **Step 1: Add section collapse state and helper**

Add three instance variables to `FilterSearchSidebar.__init__` (before `_build_ui`):

```python
self._search_collapsed: bool = False
self._filter_collapsed: bool = False
self._json_collapsed: bool = False
```

Add a `_toggle_section(name)` method:

```python
def _toggle_section(self, name: str) -> None:
    attr = f"_{name}_collapsed"
    setattr(self, attr, not getattr(self, attr))
    self._apply_collapse(name)

def _apply_collapse(self, name: str) -> None:
    collapsed = getattr(self, f"_{name}_collapsed")
    content = getattr(self, f"_{name}_content")
    content.setVisible(not collapsed)
    # Update arrow in header label
    lbl = getattr(self, f"_{name}_arrow")
    lbl.setText("▶" if collapsed else "▼")
```

- [ ] **Step 2: Rewrite `_build_ui`**

Replace the entire `_build_ui` method with the new IDE-style layout. Key structural changes:

- `self.setFixedWidth(260)` (was 280)
- Background `#090909`
- No `QScrollArea` wrapper — use `QVBoxLayout` with `addStretch()` at the bottom
- Each section is: `_make_section_block(name, title_key)` → returns `(header_widget, content_widget)`
- Term rows use a "block container" widget with rounded border

```python
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
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    # ── SEARCH ──
    search_header, self._search_content = self._make_collapsible_section("search", "sidebar_search")
    layout.addWidget(search_header)
    layout.addWidget(self._search_content)
    self._build_search_content(self._search_content)

    # 2px gap between sections
    layout.addWidget(self._make_section_gap())

    # ── FILTER ──
    filter_header, self._filter_content = self._make_collapsible_section("filter", "sidebar_filter")
    layout.addWidget(filter_header)
    layout.addWidget(self._filter_content)
    self._build_filter_content(self._filter_content)

    layout.addWidget(self._make_section_gap())

    # ── JSON KEYS ──
    json_header, self._json_content = self._make_collapsible_section("json", "sidebar_json_keys")
    layout.addWidget(json_header)
    layout.addWidget(self._json_content)
    self._build_json_content(self._json_content)

    layout.addStretch()

    scroll.setWidget(inner)
    outer.addWidget(scroll)

    # Ctrl+F: focus sidebar search
    sc = QShortcut(QKeySequence("Ctrl+F"), self)
    sc.setContext(Qt.ShortcutContext.WindowShortcut)
    sc.activated.connect(self._focus_first_search)

    self.retranslate()
```

- [ ] **Step 3: Add section builder helpers**

```python
def _make_collapsible_section(self, name: str, title_key: str) -> tuple[QWidget, QWidget]:
    """Returns (header_widget, content_widget). Stores _<name>_arrow label."""
    header = QWidget()
    header.setStyleSheet(
        "QWidget { background: #111; border: none; }"
        "QWidget:hover { background: #151515; }"
    )
    header.setCursor(Qt.CursorShape.PointingHandCursor)
    header.setFixedHeight(32)

    h = QHBoxLayout(header)
    h.setContentsMargins(12, 0, 12, 0)
    h.setSpacing(8)

    arrow = QLabel("▼")
    arrow.setStyleSheet(f"color: {C_MUTED}; font-size: 9px; background: transparent;")
    setattr(self, f"_{name}_arrow", arrow)

    title = QLabel()
    title.setStyleSheet(
        f"color: #999; font-size: 11px; font-weight: 500; background: transparent;"
    )
    title.setProperty("i18n_key", title_key)
    self._section_labels.append(title)

    badge = QLabel("0")
    badge.setStyleSheet(
        f"color: {C_MUTED}; font-size: 9px; background: #1a1a1a; "
        "border-radius: 8px; padding: 1px 6px;"
    )
    setattr(self, f"_{name}_badge", badge)

    h.addWidget(arrow)
    h.addWidget(title)
    h.addStretch()
    h.addWidget(badge)

    # Click to collapse
    header.mousePressEvent = lambda _ev, n=name: self._toggle_section(n)

    content = QWidget()
    content.setStyleSheet("background: #090909;")
    setattr(self, f"_{name}_content", content)

    return header, content

def _make_section_gap(self) -> QWidget:
    gap = QWidget()
    gap.setFixedHeight(2)
    gap.setStyleSheet("background: #0d0d0d;")
    return gap

def _add_btn_style(self) -> str:
    return (
        f"QPushButton {{ background: transparent; color: {C_MUTED}; "
        f"border: 1px solid #2a2a2a; border-radius: 3px; "
        f"font-size: 10px; padding: 2px 8px; }}"
        f"QPushButton:hover {{ color: {C_TEXT}; border-color: #444; }}"
    )

def _nav_btn_style(self) -> str:
    return (
        f"QPushButton {{ background: transparent; color: {C_MUTED}; "
        f"border: none; font-size: 12px; padding: 2px 6px; }}"
        f"QPushButton:hover {{ color: {C_TEXT}; }}"
    )

def _term_block_style(self) -> str:
    return (
        f"background: #161616; border: 1px solid #2c2c2c; border-radius: 5px;"
    )
```

- [ ] **Step 4: Build section content widgets**

```python
def _build_search_content(self, parent: QWidget) -> None:
    vbox = QVBoxLayout(parent)
    vbox.setContentsMargins(10, 8, 10, 8)
    vbox.setSpacing(4)

    # Term rows block
    self._search_block = QWidget()
    self._search_block.setStyleSheet(self._term_block_style())
    self._search_rows_layout = QVBoxLayout(self._search_block)
    self._search_rows_layout.setContentsMargins(0, 0, 0, 0)
    self._search_rows_layout.setSpacing(0)
    vbox.addWidget(self._search_block)
    self._add_search_row("")   # initial empty row

    # Add AND/OR buttons
    add_row = QHBoxLayout()
    add_row.setSpacing(4)
    add_row.setContentsMargins(0, 0, 0, 0)
    self._btn_add_search_and = QPushButton()
    self._btn_add_search_and.clicked.connect(lambda: self._add_search_row("AND"))
    self._btn_add_search_or = QPushButton()
    self._btn_add_search_or.clicked.connect(lambda: self._add_search_row("OR"))
    for btn in (self._btn_add_search_and, self._btn_add_search_or):
        btn.setFixedHeight(22)
        btn.setStyleSheet(self._add_btn_style())
    add_row.addWidget(self._btn_add_search_and)
    add_row.addWidget(self._btn_add_search_or)
    add_row.addStretch()
    vbox.addLayout(add_row)

    # Prev / Next / hits inline
    nav_row = QHBoxLayout()
    nav_row.setSpacing(4)
    nav_row.setContentsMargins(0, 2, 0, 0)
    self._btn_prev = QPushButton()
    self._btn_next = QPushButton()
    self._lbl_hits = QLabel()
    self._lbl_hits.setStyleSheet(f"color: {C_MUTED}; font-size: 10px;")
    for btn in (self._btn_prev, self._btn_next):
        btn.setFixedHeight(22)
        btn.setStyleSheet(self._nav_btn_style())
    self._btn_prev.clicked.connect(self._search_prev)
    self._btn_next.clicked.connect(self._search_next_match)
    nav_row.addWidget(self._btn_prev)
    nav_row.addWidget(self._btn_next)
    nav_row.addWidget(self._lbl_hits)
    nav_row.addStretch()
    vbox.addLayout(nav_row)

def _build_filter_content(self, parent: QWidget) -> None:
    vbox = QVBoxLayout(parent)
    vbox.setContentsMargins(10, 8, 10, 8)
    vbox.setSpacing(4)

    self._filter_block = QWidget()
    self._filter_block.setStyleSheet(self._term_block_style())
    self._filter_rows_layout = QVBoxLayout(self._filter_block)
    self._filter_rows_layout.setContentsMargins(0, 0, 0, 0)
    self._filter_rows_layout.setSpacing(0)
    vbox.addWidget(self._filter_block)
    self._add_filter_row("")   # initial empty row

    add_row = QHBoxLayout()
    add_row.setSpacing(4)
    add_row.setContentsMargins(0, 0, 0, 0)
    self._btn_add_filter_and = QPushButton()
    self._btn_add_filter_and.clicked.connect(lambda: self._add_filter_row("AND"))
    self._btn_add_filter_or = QPushButton()
    self._btn_add_filter_or.clicked.connect(lambda: self._add_filter_row("OR"))
    self._btn_add_filter_kv = QPushButton()
    self._btn_add_filter_kv.clicked.connect(lambda: self._add_filter_row("AND", mode="kv"))
    for btn in (self._btn_add_filter_and, self._btn_add_filter_or, self._btn_add_filter_kv):
        btn.setFixedHeight(22)
        btn.setStyleSheet(self._add_btn_style())
    add_row.addWidget(self._btn_add_filter_and)
    add_row.addWidget(self._btn_add_filter_or)
    add_row.addWidget(self._btn_add_filter_kv)
    add_row.addStretch()
    vbox.addLayout(add_row)

    live_row = QHBoxLayout()
    live_row.setContentsMargins(0, 2, 0, 0)
    self._cb_live = QCheckBox()
    self._cb_live.setChecked(True)
    self._cb_live.setStyleSheet(f"color: {C_MUTED}; font-size: 10px;")
    live_row.addWidget(self._cb_live)
    live_row.addStretch()
    vbox.addLayout(live_row)

def _build_json_content(self, parent: QWidget) -> None:
    vbox = QVBoxLayout(parent)
    vbox.setContentsMargins(10, 8, 10, 10)
    vbox.setSpacing(4)

    self._json_container = QWidget()
    self._json_container.setStyleSheet("background: transparent;")
    self._json_layout = QVBoxLayout(self._json_container)
    self._json_layout.setContentsMargins(0, 0, 0, 0)
    self._json_layout.setSpacing(4)
    self._lbl_json_ph = QLabel()
    self._lbl_json_ph.setStyleSheet(f"color: {C_MUTED}; font-size: 10px;")
    self._json_layout.addWidget(self._lbl_json_ph)
    vbox.addWidget(self._json_container)
```

- [ ] **Step 5: Update `_add_search_row` / `_add_filter_row` to add dividers between rows**

Inside `_add_search_row`, add a horizontal separator before new rows (not the first):

```python
def _add_search_row(self, operator: str) -> None:
    if self._search_term_widgets:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: #2c2c2c; max-height: 1px;")
        self._search_rows_layout.addWidget(sep)
    row = _TermRowWidget(operator, parent=self)
    row.setContentsMargins(8, 4, 4, 4)
    row.changed.connect(self._on_search_changed)
    row.remove_requested.connect(lambda r=row: self._remove_search_row(r))
    self._search_term_widgets.append(row)
    self._search_rows_layout.addWidget(row)
    row.set_placeholder(i18n.tr("sidebar_term_ph"))
```

Same pattern for `_add_filter_row` (but also support `mode` and `prefill_key` from Task 3).

For `_remove_search_row` / `_remove_filter_row`, also remove the separator widget above the removed row:

```python
def _remove_search_row(self, row: _TermRowWidget) -> None:
    if len(self._search_term_widgets) == 1:
        return
    idx = self._search_term_widgets.index(row)
    self._search_term_widgets.remove(row)
    layout = self._search_rows_layout
    # Remove the widget itself
    layout.removeWidget(row)
    row.deleteLater()
    # Remove separator that preceded it (if not first row, the separator was before this widget)
    # Find and remove orphaned separators by rebuilding: simpler to clear and re-add
    self._rebuild_row_block(
        self._search_block,
        self._search_rows_layout,
        self._search_term_widgets,
        "search",
    )
    self._on_search_changed()
```

Add `_rebuild_row_block` helper that clears the layout and re-adds all rows with separators between them:

```python
def _rebuild_row_block(
    self,
    block: QWidget,
    layout: QVBoxLayout,
    widgets: list[_TermRowWidget],
    section: str,
) -> None:
    """Clear layout and re-insert all term rows with separators between them."""
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w and w not in widgets:
            w.deleteLater()
    for i, w in enumerate(widgets):
        if i > 0:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("color: #2c2c2c; max-height: 1px;")
            layout.addWidget(sep)
        layout.addWidget(w)
```

Write `_remove_filter_row` explicitly (mirrors `_remove_search_row` but for the filter section):

```python
def _remove_filter_row(self, row: _TermRowWidget) -> None:
    if len(self._filter_term_widgets) == 1:
        return
    self._filter_term_widgets.remove(row)
    self._filter_rows_layout.removeWidget(row)
    row.deleteLater()
    self._rebuild_row_block(
        self._filter_block,
        self._filter_rows_layout,
        self._filter_term_widgets,
        "filter",
    )
    self._on_filter_changed()
```

- [ ] **Step 6: Update JSON key chips style**

In `_rebuild_json_chips`, update the chip button style:

```python
btn.setFixedHeight(22)
btn.setStyleSheet(
    f"QPushButton {{ background: transparent; color: {C_TRACE}; "
    f"border: 1px solid #ce93d833; border-radius: 10px; font-size: 10px; "
    f"padding: 1px 8px; text-align: left; }}"
    f"QPushButton:hover {{ background: #ce93d811; border-color: #ce93d866; }}"
)
```

PyQt6 has no built-in flow/wrap layout. Use `QVBoxLayout` — chips stack vertically. Each chip is compact (22px height) so the list scrolls naturally within the sidebar's `QScrollArea`. Horizontal chip-wrapping is deferred to a future improvement.

- [ ] **Step 7: Update badge counts**

Add badge update helpers called from existing methods:

```python
def _update_search_badge(self) -> None:
    n = len(self._search_matches)
    self._search_badge.setText(str(n) if n else "")

def _update_filter_badge(self) -> None:
    active = sum(1 for w in self._filter_term_widgets if w.to_term_row().text or w.to_term_row().key)
    self._filter_badge.setText(str(active) if active else "")

def _update_json_badge(self) -> None:
    n = self._json_layout.count() - (1 if self._lbl_json_ph.isVisible() else 0)
    self._json_badge.setText(str(max(0, n)))
```

Call `_update_search_badge()` from `_update_hits_label()`, `_update_filter_badge()` from `_on_filter_changed()`, and `_update_json_badge()` from `_rebuild_json_chips()`.

- [ ] **Step 8: Update `retranslate`**

```python
def retranslate(self) -> None:
    for lbl in self._section_labels:
        key = lbl.property("i18n_key")
        if key:
            lbl.setText(i18n.tr(key))
    self._btn_add_search_and.setText(i18n.tr("sidebar_add_and"))
    self._btn_add_search_or.setText(i18n.tr("sidebar_add_or"))
    self._btn_prev.setText("▲")
    self._btn_next.setText("▼")
    self._btn_add_filter_and.setText(i18n.tr("sidebar_add_and"))
    self._btn_add_filter_or.setText(i18n.tr("sidebar_add_or"))
    self._btn_add_filter_kv.setText("+ key=val")
    self._cb_live.setText(i18n.tr("sidebar_live_filter"))
    self._lbl_json_ph.setText(i18n.tr("sidebar_json_ph"))
    for w in self._search_term_widgets + self._filter_term_widgets:
        w.set_placeholder(i18n.tr("sidebar_term_ph"))
    self._update_hits_label()
```

- [ ] **Step 9: Run all tests**

```bash
python3 -m pytest -v
```
Expected: all pass

- [ ] **Step 10: Lint**

```bash
python3 -m ruff check . --fix
```

- [ ] **Step 11: Commit**

```bash
git add ui.py
git commit -m "feat: sidebar visual redesign — IDE style, collapsible sections, compact chips"
```

---

## Task 5: Final integration check

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

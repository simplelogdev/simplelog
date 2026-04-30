# Filter & Search Sidebar — Design Spec

**Date:** 2026-03-25
**Status:** Approved (rev 4 — post spec-review round 3)
**Scope:** Global right sidebar in SimpleLog (PyQt6) providing multi-term filter and search on the active log viewer.

---

## 1. Overview

Add a collapsible right sidebar to `MainWindow` containing two panels:

1. **Filter** — hide/show log lines based on one or more text terms (AND/OR conditions). JSON keys detected from log content are shown as clickable chips to build filter terms quickly.
2. **Search** — find and navigate occurrences of one or more terms (AND/OR), highlighted in the viewer. Replaces the existing single-term search bar in the `LogViewer` toolbar.

The sidebar is **global**: one instance per window, always operating on the currently active `LogViewer`. Filter/search terms persist across viewer switches (the same terms are re-applied when you activate a different tab).

---

## 2. Architecture

### 2.1 New widget: `FilterSearchSidebar`

A `QWidget` placed directly in the root `QHBoxLayout` (in `MainWindow._build_ui`) **after** `self._splitter`. It has a **fixed width of 280 px** and is not managed by the splitter. It is not a child of `self._splitter`. Visibility is toggled via a button or `Ctrl+Shift+F`; `Ctrl+F` focuses the first search term input (see §2.5).

Internal layout (top to bottom):

```
┌──────────────────────────────┐
│  🔍 SEARCH                   │
│  [term input]          [×]   │
│  AND [term input]      [×]   │
│  [+ AND]  [+ OR]             │
│  [▲ Prev]  [▼ Next]  n hits  │
├──────────────────────────────┤
│  🔧 FILTER                   │
│  [term input]          [×]   │
│  OR  [term input]      [×]   │
│  [+ AND]  [+ OR]             │
│  [✓ Live]                    │
├──────────────────────────────┤
│  {} JSON KEYS                │
│  [requestId]  [level]        │
│  [userId]  [service]  ...    │
└──────────────────────────────┘
```

State held by the sidebar:
- `_filter_terms: list[TermRow]`
- `_search_terms: list[TermRow]`
- `_active_viewer: LogViewer | None`
- `_search_matches: list[tuple[int, int]]` — sorted `(position, length)` in document order
- `_search_match_index: int` — current position in `_search_matches`

### 2.2 `TermRow`

```python
@dataclass
class TermRow:
    text: str
    operator: str  # "AND" | "OR" | "" — empty string for the first term (operator is ignored)
```

Using `""` as the sentinel for the first term makes it explicit at the type level that no operator applies.

### 2.3 Changes to `LogViewer`

| Addition | Purpose |
|---|---|
| `_raw_events: deque[tuple[int, str]]` | Raw event buffer; `deque(maxlen=_MAX_LINES)` — O(1) cap, no manual trim |
| `_json_keys: set[str]` | Accumulated top-level JSON keys |
| `json_keys_updated = pyqtSignal(set)` | Emitted when new keys are found |
| `lines_appended = pyqtSignal()` | Emitted after each `append_events` call that writes new lines to display (not during `_filtering`) |
| `_filtering: bool` | Guard set during `apply_filter` to block concurrent `QTextEdit` writes |
| `_pending_during_filter: list[tuple[int,str]]` | Events buffered while `_filtering` is True |
| `filter_applied = pyqtSignal()` | Emitted after `apply_filter` finishes (signals sidebar to refresh search) |
| `apply_filter(terms: list[TermRow]) -> None` | Re-render buffer through filter (see §3) |
| `get_json_keys() -> set[str]` | Returns current key set |
| `apply_search(terms: list[TermRow]) -> list[tuple[int,int]]` | Updates search highlighter, returns sorted match positions |
| `search_next() / search_prev()` | Delegate to sidebar navigation (sidebar owns match list) |

`append_events` is modified:
1. Always append to `_raw_events` (deque handles overflow automatically).
2. If `_filtering` is True: append to `_pending_during_filter` and return — do **not** write to `QTextEdit`.
3. Otherwise: apply the current filter terms to each incoming event and write matching lines to `QTextEdit` as before.
4. Run JSON key detection (§5) on each new line.

After `apply_filter` finishes, it processes `_pending_during_filter` (flushes matching events to `QTextEdit`) and clears the list.

**Removed from `LogViewer`:**
- `self.search_input` (QLineEdit) — widget, layout slot, `_search_next` method, the `Ctrl+F` `QShortcut` registered in `_build_ui` (line ~1120 of `ui.py`), and all references in `retranslate` (`viewer_search_ph` call at line ~1132). This shortcut is **on `LogViewer`**, not on `MainWindow`; removing it here eliminates the conflict with the sidebar's own `Ctrl+F` registration.

### 2.4 Changes to `LogHighlighter`

`RULES` remains a **class-level constant** (shared, read-only). A separate **instance-level** `_search_rules: list[tuple[re.Pattern, str, bool]]` list is added in `__init__` (initially empty).

`highlightBlock` runs all `RULES` first, then all `_search_rules`. Search rules use a **background-only** `QTextCharFormat` (`setBackground(QColor("#3a3a00"))`, no foreground override), so severity colour is always preserved.

New method: `set_search_terms(terms: list[TermRow]) -> None` — rebuilds `_search_rules` from the term list and calls `self.rehighlight()`.

### 2.5 Changes to `MainWindow`

- `_build_ui`: add `FilterSearchSidebar` to the right of `self._splitter` in the root `QHBoxLayout`.
- `_make_pane`: add `tabs.currentChanged.connect(lambda _, t=tabs: self._on_active_viewer_changed(t))` alongside the existing `_set_active_pane` connection.
- `_set_active_pane`: call `self._on_active_viewer_changed(pane)` (replaces direct `_active_pane` assignment where possible).
- `_add_tab`: after adding the viewer, call `self._on_active_viewer_changed(target)`.
- New `_on_active_viewer_changed(pane: QTabWidget)`: sets `_active_pane`, resolves `viewer = pane.currentWidget()`, calls `self._sidebar.set_active_viewer(viewer)`.
- `_action_paste` and `self._act_paste`: remove entirely — both the method and the QAction from `_build_menubar`, including the Edit → Paste menu item. `Ctrl+V` then falls through naturally to the focused widget (standard Qt behaviour). The `action_paste` i18n key (EN/FR) is also removed.
- `_LogTextEdit`: keep the subclass as-is; the `enter_pressed` signal becomes unused after search bar removal but is retained to avoid removing useful future extension points. The connection `self.text_edit.enter_pressed.connect(self._insert_separator)` remains.
- Shortcuts: `Ctrl+Shift+F` toggles sidebar visibility. `Ctrl+F` is registered in `FilterSearchSidebar` with `Qt.ShortcutContext.WindowShortcut` so it fires regardless of which pane has focus, and focuses the first search `TermRow` input. The per-`LogViewer` `Ctrl+F` is removed (see §2.3).
- `_close_tab` / `_stop_viewer`: when the tab being closed is the currently active viewer, call `self._sidebar.set_active_viewer(None)` before removing the widget, then immediately re-point to `pane.currentWidget()` if another tab remains in the same pane.

### 2.6 Signal wiring in `set_active_viewer`

```python
def set_active_viewer(self, viewer: LogViewer | None):
    if self._active_viewer is not None:
        self._active_viewer.json_keys_updated.disconnect(self._on_json_keys_updated)
        self._active_viewer.lines_appended.disconnect(self._on_lines_appended)
        self._active_viewer.filter_applied.disconnect(self._refresh_search)
    self._active_viewer = viewer
    if viewer is not None:
        viewer.json_keys_updated.connect(self._on_json_keys_updated)
        viewer.lines_appended.connect(self._on_lines_appended)
        viewer.filter_applied.connect(self._refresh_search)
        self._on_json_keys_updated(viewer.get_json_keys())   # show existing keys
        viewer.apply_filter(self._filter_terms)              # apply current terms
        # _refresh_search will be triggered by filter_applied signal above
```

---

## 3. Filter Logic

### 3.1 Matching a single line (case-insensitive)

```python
def _line_matches(line: str, terms: list[TermRow]) -> bool:
    if not terms:
        return True
    low = line.lower()
    result = terms[0].text.lower() in low
    for term in terms[1:]:
        hit = term.text.lower() in low
        result = (result and hit) if term.operator == "AND" else (result or hit)
    return result
```

### 3.2 Live filter with debounce, race protection, and UI-freeze mitigation

Filter is applied live as the user types, **debounced 150 ms** to avoid re-rendering on every keystroke.

`apply_filter(terms)`:
1. Set `_filtering = True`.
2. Clear `QTextEdit`.
3. Iterate `_raw_events` in chunks of **500 lines**. After each chunk, call `QApplication.processEvents()` to keep the UI responsive. Format each matching line (respecting `timestamps_cb.isChecked()` — same logic as `append_events`) and insert it into the `QTextEdit`.
4. Set `_filtering = False`.
5. Flush `_pending_during_filter` through the filter into `QTextEdit`; clear the list.
6. Notify the sidebar to refresh search highlights: emit a `filter_applied = pyqtSignal()` signal that the sidebar connects to (alongside `lines_appended` and `json_keys_updated`) in `set_active_viewer`. On receipt, the sidebar calls `_refresh_search()` to recompute match positions against the newly rendered document.

If `_raw_events` is empty, steps 3 and 5 produce nothing; the method is effectively a no-op.

`filter_applied` is added to the `LogViewer` signals table (§2.3) and connected/disconnected in `set_active_viewer` (§2.6).

### 3.3 JSON key filter

Clicking a JSON key chip in the sidebar appends a new filter term row pre-filled with the key name. The user can edit the term freely (e.g., `"userId": "abc"` substring match).

---

## 4. Search Logic

### 4.1 Highlighting

Same multi-term AND/OR model. `apply_search(terms)` builds a combined pattern per-term, runs `re.finditer` over the full document `toPlainText()`, collects all `(position, length)` match spans (sorted by position), stores them in `FilterSearchSidebar._search_matches`, and calls `LogHighlighter.set_search_terms(terms)` to highlight all matches (yellow background `#3a3a00`).

Returns the sorted match list so the sidebar can display the count.

### 4.2 Navigation

`search_next` / `search_prev` walk `FilterSearchSidebar._search_matches` by incrementing/decrementing `_search_match_index` (wrapping). For each match, a `QTextCursor` is positioned using `cursor.setPosition(pos); cursor.setPosition(pos+length, KeepAnchor)` and `QTextEdit.setTextCursor(cursor)` to scroll and select the match.

Match count displayed as `"{n:,} résultats"` / `"{n:,} hits"` beneath the navigation buttons. `"Aucun résultat"` / `"No results"` when `_search_matches` is empty.

Search is re-run whenever:
- A search term text changes (debounced 150 ms).
- The active viewer changes (via `_refresh_search` in `set_active_viewer`).
- New lines arrive in the active viewer: `LogViewer` emits `lines_appended = pyqtSignal()` at the end of `append_events` (only when not in `_filtering` mode, and only when new lines were actually written to the display). The sidebar connects/disconnects `lines_appended` in `set_active_viewer` alongside `json_keys_updated`, and runs a **full re-scan** (debounced 300 ms) on this signal. A full re-scan is used rather than incremental extension because the simplicity benefit outweighs the performance cost at the 10 000-line cap.

---

## 5. JSON Key Detection

On each `append_events` call, for each new line, run (outside the `_filtering` guard — detection always happens):

1. Try `json.loads(line)` — if it parses as a dict, extract `set(result.keys())`.
2. Otherwise (fallback): `re.findall(r'"([\w_-]+)"\s*:', line)` — extracts candidate key names without attempting to parse the full JSON structure. Best-effort; may include false positives from non-JSON content.

New keys are unioned into `_json_keys`. If `_json_keys` grows, emit `json_keys_updated(_json_keys.copy())`.

The sidebar listens to `json_keys_updated` on the active viewer and re-renders its key chip panel (sorted alphabetically, max 50 chips to avoid overflow).

---

## 6. Sidebar Toggle

- `Ctrl+Shift+F`: toggles sidebar visibility.
- `Ctrl+F`: focuses the first search `TermRow` input (registered on `FilterSearchSidebar`; the old per-`LogViewer` `Ctrl+F` shortcut is removed).
- The `help_content` i18n strings (EN and FR) must be updated to reflect the new `Ctrl+F` behaviour.

State is not persisted across sessions (workspace feature will handle layout persistence).

---

## 7. i18n

New translation keys (EN/FR):

| Key | EN | FR |
|---|---|---|
| `sidebar_search` | Search | Recherche |
| `sidebar_filter` | Filter | Filtrer |
| `sidebar_json_keys` | JSON Keys | Clés JSON |
| `sidebar_add_and` | + AND | + ET |
| `sidebar_add_or` | + OR | + OU |
| `sidebar_prev` | ▲ Prev | ▲ Préc |
| `sidebar_next` | ▼ Next | ▼ Suiv |
| `sidebar_hits` | {n:,} hits | {n:,} résultats |
| `sidebar_no_hits` | No results | Aucun résultat |
| `sidebar_term_ph` | Term… | Terme… |
| `sidebar_live_filter` | Live | En direct |
| `sidebar_json_ph` | Detected keys… | Clés détectées… |

**Keys to remove:** `viewer_search_ph` (search bar gone from toolbar), `action_paste` (Edit → Paste menu item removed).

**Keys to update:** `help_content` EN/FR — reflect `Ctrl+F` → focuses sidebar search, `Ctrl+Shift+F` → toggles sidebar.

---

## 8. Out of Scope

- Regex filter mode (future)
- Negation / exclude filter (future)
- Per-viewer saved filter sets (future, workspace feature)
- Filter on CloudWatch server side (kept as-is via existing `filter_input`)

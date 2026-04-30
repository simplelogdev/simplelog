# SimpleLog

A fast, Material Design log viewer for **AWS CloudWatch**, **local log files**, and **piped stdin** — built with PyQt6.

---

## Features

- **Three log sources** — CloudWatch streams, local files, and piped stdin in a unified interface
- **Tabs + split panes** — each tab holds one or more panes; open logs side-by-side (vertical) or stacked (horizontal) inside the active tab
- **Configurable tail** — load only the last N lines of large files to prevent UI freezing (default: 100)
- **Live tailing** — files and CloudWatch streams are polled continuously for new events
- **Syntax highlighting** — color-coded `ERROR`, `WARN`, `INFO`, `DEBUG`, `TRACE`, timestamps, JSON keys
- **Sidebar search** — incremental search with `Ctrl+F`, previous/next navigation, hit count
- **Sidebar filter** — live filter with AND / OR logic; matching lines only are shown
- **JSON key detection** — detected JSON keys listed automatically for quick filtering
- **Workspaces** — save and restore full sessions (sources, split layout, filters)
- **Language** — EN / FR via the Language menu, preference persisted across restarts
- **Material Design dark theme**

---

## Requirements

- Python 3.11+
- PyQt6 >= 6.6
- AWS credentials configured (for CloudWatch only — `~/.aws/credentials` or environment variables)

---

## Installation

```bash
git clone https://github.com/sindus/simplelog.git
cd simplelog
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

---

## Usage

### GUI mode (CloudWatch browser)

```bash
python main.py
```

### Open one or more log files

```bash
python main.py /var/log/syslog /var/log/auth.log
```

### Pipe stdin

```bash
journalctl -f | python main.py
kubectl logs -f my-pod | python main.py
```

---

## CLI Reference

```
simplelog [--split MODE] [--tail N] [FILE ...]
command | simplelog [--split MODE]
```

### Arguments

| Argument | Default | Description |
|---|---|---|
| `FILE ...` | — | One or more log file paths. Glob patterns are not expanded — use your shell: `simplelog logs/*.log`. |
| `--split MODE` | `tab` | How to lay out files on startup. See values below. |
| `--tail N` | `100` | Lines to load from the **end** of each file. Prevents freezing on large files. |

### `--split` values

| Value | Layout | Description |
|---|---|---|
| `tab` | *(default)* | Each file opens as a new tab. |
| `vertical` | `│` divider | Files open as panes split side-by-side inside the same tab. |
| `horizontal` | `─` divider | Files open as panes split top/bottom inside the same tab. |

> The split mode selected via `--split` is also reflected in the sidebar radio buttons inside the app.

### Examples

```bash
# Launch the CloudWatch browser (no arguments)
simplelog

# Tail a single file
simplelog /var/log/syslog

# Load the last 500 lines of a large file
simplelog --tail 500 /var/log/nginx/access.log

# Open multiple files as tabs
simplelog app.log worker.log scheduler.log

# Open two files side-by-side (vertical split)
simplelog --split vertical app.log error.log

# Open two files stacked (horizontal split)
simplelog --split horizontal service-a.log service-b.log

# Split + custom tail
simplelog --split vertical --tail 1000 app.log error.log

# Pipe any command's output
journalctl -f | simplelog
kubectl logs -f my-pod | simplelog
docker logs -f my-container | simplelog

# Pipe with filtering
tail -f /var/log/syslog | grep -i error | simplelog
```

### Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+F` | Open / focus sidebar search |
| `Ctrl+Shift+F` | Toggle sidebar |
| `Ctrl+W` | Close all open logs |
| `Enter` / `▼ Next` | Find next match |
| `▲ Prev` | Find previous match |
| `Escape` | Close search bar |

---

## Split panes

Each tab can contain multiple panes arranged in a splitter. The split mode is choosable from the sidebar before opening a source:

- **New tab** — opens in a new tab (default)
- **Split ↔ side by side** — adds a pane to the right inside the current tab
- **Split ↕ top / bottom** — adds a pane below inside the current tab

Closing the last pane in a tab closes the tab automatically. Panes can be resized by dragging the splitter handle, and closed individually with the ✕ button in their toolbar.

---

## Sidebar

The sidebar (toggle: `Ctrl+Shift+F`) has three panels:

### Search
Incremental full-text search across visible log lines. Shows hit count and supports ▲ / ▼ navigation.

### Filter
Live filter that hides non-matching lines. Multiple terms can be combined with **AND** or **OR** logic. Enable **Live** to also filter incoming lines as they arrive.

### JSON Keys
When log lines contain JSON, detected keys are listed automatically. Click a key to add it as a filter term.

---

## Workspaces

The Workspaces panel lets you save and restore complete sessions:

- **Save** — captures the current open sources (files, CloudWatch streams), their split layout, and filter state
- **Open** — re-opens all sources in the saved layout in a new tab
- **Rename / Delete** — manage saved workspaces

Workspaces are persisted to `~/.config/simplelog/workspaces.json`.

---

## CloudWatch

1. Select an AWS **profile** and **region**, then click **Connect**
2. Browse and filter **log groups**
3. Select a **log stream** (or "All streams")
4. Set lookback window, poll interval, and optional filter pattern
5. Choose how to open it (tab or split), then click **Open ↗**

---

## Project layout

```
simplelog/
├── main.py          # Entry point, CLI argument parsing
├── ui.py            # All PyQt6 UI components
├── workers.py       # Background QThread workers (file, CloudWatch, stdin, updater)
├── cloudwatch.py    # boto3 CloudWatch Logs helpers
├── i18n.py          # EN / FR translation system
├── version.py       # Single source of truth for the app version
├── requirements.txt # Runtime dependencies
└── tests/           # Unit tests
```

---

## Development

### Install dev dependencies

```bash
pip install -r requirements-dev.txt
```

### Run tests

```bash
pytest -v
```

### Run tests with coverage

```bash
pytest -v --cov=. --cov-report=term-missing
```

### Lint

```bash
ruff check .
```

---

## Uninstall

### macOS (.dmg)

```bash
rm -rf /Applications/SimpleLog.app
```

### Linux — Debian / Ubuntu (.deb)

```bash
sudo apt remove simplelog
# or, if installed directly with dpkg:
sudo dpkg -r simplelog
```

### Linux — AppImage

```bash
rm -f ~/.local/bin/simplelog
```

---

## License

MIT

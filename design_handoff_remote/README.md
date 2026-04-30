# Handoff: Remote Connection Manager Redesign

## Overview

This handoff documents the redesign of the **Remote** section of SimpleLog (`ui.py`).

The current implementation has each provider (CloudWatch, GCP, Azure, SSH, Docker, Vercel) as a separate `QWidget` panel shown in a `QStackedWidget`. The new design replaces this with:

1. A **unified connection list** in the left sidebar — all providers collapsed into expandable groups
2. A **single modal dialog** (`QDialog`) for adding connections — step 1: pick provider, step 2: fill fields — with two save options
3. A **provider detail panel** (in the sidebar) showing connections for one provider with add/delete

The rest of the UI (nav rail, main log viewer, right sidebar) is **unchanged**.

---

## About the Design Files

`simplelog-remote.html` is a **high-fidelity interactive prototype** built in HTML/React. It is a design reference only — not production code. The task is to **recreate this UI in the existing PyQt6 codebase** (`ui.py`), using PyQt6 widgets, the existing color constants, and established patterns (`make_card`, `_primary_btn`, `_ghost_btn`, `_ProfileBar`, etc.).

**Fidelity: High-fidelity.** Colors, spacing, typography, hover states, and animations should match the prototype as closely as PyQt6 allows.

---

## Design Tokens (from existing `ui.py` — do not change)

```python
C_BG         = "#0d0d10"
C_RAIL       = "#080810"
C_SIDE       = "#111116"
C_PANEL      = "#14141a"
C_CARD       = "#1a1a24"
C_STATUS     = "#090910"
C_BORDER     = "rgba(255,255,255,18)"
C_ACCENT     = "#5b8fff"
C_ACCENT_DIM = "rgba(91,143,255,38)"
C_TEXT       = "#d4d4e0"
C_MUTED      = "#52526a"
C_SEL_BG     = "rgba(91,143,255,31)"
C_ERR        = "#f07878"
C_WARN       = "#f0c060"
C_INFO       = "#56cf80"
C_TRACE      = "#b07cf0"
C_TS         = "#50c8dc"

Font:        "Inter", sans-serif — 12px base
Mono font:   "JetBrains Mono", monospace — 11px for field values
Border radius (cards): 10px
Border radius (buttons): 6px
Border radius (inputs): 5px
```

---

## Architecture: What Changes in `ui.py`

### Remove
- `CloudWatchPanel`, `GCPPanel`, `AzurePanel`, `SSHPanel`, `DockerPanel`, `VercelPanel` individual widgets inside the remote stacked widget
- The existing provider-picker home screen in the remote stacked widget

### Add
1. **`RemoteHomePanel(QWidget)`** — the new sidebar panel (replaces the stacked widget contents)
2. **`AddConnectionDialog(QDialog)`** — two-step modal (provider pick → form)
3. **`ProviderDetailWidget(QWidget)`** — shown in sidebar when a provider group is expanded/opened

### Keep unchanged
- `creds_store.py` — used for persisting connections
- `profiles_store.py` — keep for backward compat if needed
- `NavRail`, `FilePanel`, `WorkspacePanel`, `FilterSearchSidebar`, `LogViewer` — untouched
- All color constants and helper functions (`make_card`, `_primary_btn`, etc.)

---

## Screen 1 — Remote Home Panel (Sidebar)

**Class:** `RemoteHomePanel(QWidget)`  
**Width:** fits the existing left sidebar (~268px)  
**Background:** `C_SIDE`

### Layout (top to bottom)

```
┌─────────────────────────────┐
│  Remote            [+ Add]  │  ← Header row
├─────────────────────────────┤
│  ┌─ CloudWatch ──── 2 ──▼─┐ │  ← ProviderGroupRow (expanded)
│  │  ● prod-us-east-1      │ │    ConnRow
│  │  ● staging-eu-west-1   │ │    ConnRow
│  │  + Add connection       │ │    AddInlineRow
│  └────────────────────────┘ │
│  ┌─ GCP ──────────── 1 ──▼─┐│
│  │  ● gcp-prod             ││
│  │  + Add connection        ││
│  └────────────────────────┘ │
│  ┌─ SSH ──────────── 1 ──▼─┐│
│  │  ● prod-server          ││
│  └────────────────────────┘ │
│  ┌─ Vercel ─────── 1 ──▼──┐ │
│  │  ● vercel-main          │ │
│  └────────────────────────┘ │
└─────────────────────────────┘
```

### Header row
- Label "Remote" — `C_TEXT`, 15px, weight 700
- Button "Add" — `_primary_btn("Add")`, full width, icon: `+` prefix
- Bottom border: `1px solid C_BORDER`
- Padding: 14px all sides, 10px gap between label and button

### Provider Group Row (`ProviderGroupRow`)
Each saved-connections provider renders as a collapsible group:

**Header button** (full width, flat):
- Background: `C_CARD` (hover: slightly lighter — `rgba(255,255,255,8)` over card)
- Height: 36px, padding: 0 10px
- Left: provider icon (20×20 rounded rect, `provider_color + "18"` bg, `provider_color + "30"` border) + name (`C_TEXT`, 12px, 600)
- Right: count badge (`C_MUTED`, 10px) + chevron (▼ when expanded, ▶ when collapsed)
- Click: toggle expanded state

**Connection rows** (only when expanded):
- Indent: 38px left padding
- Height: 30px
- Left: green dot (5×5, `C_INFO`, glow `C_INFO + "88"`) + name (`#b0b0c0`, 11.5px mono) + subtitle (`C_MUTED`, 10px)
- Right (on hover only): delete button — ghost, turns `C_ERR` on hover, requires confirm click
- Background: `rgba(17,17,22,0.6)`, hover: `rgba(255,255,255,0.03)`
- Top border: `1px solid rgba(255,255,255,0.05)`

**"Add connection" inline row** (bottom of expanded group):
- Indent: 38px, height: 28px
- Text: "+ Add connection", `C_MUTED` → `C_ACCENT` on hover
- Background: transparent → `rgba(91,143,255,0.05)` on hover
- Click: opens `AddConnectionDialog` pre-selected on this provider

**Delete confirmation:** Single-click sets confirm state (button turns red, shows "Confirm"). Second click deletes. Mouse leave resets confirm state.

### Empty state (no connections at all)
- Centered in panel
- Icon: remote SVG (dimmed, opacity 0.2)
- Text: "No remote connections" (`C_MUTED`, 12px)
- Subtext: "Click Add to connect a provider" (`#3a3a4a`, 11px)

---

## Screen 2 — Add Connection Dialog

**Class:** `AddConnectionDialog(QDialog)`  
**Modal:** Yes (`exec()`)  
**Size:** 500×auto (step 1), 480×auto (step 2)  
**Background:** `#13131a`  
**Border:** `1px solid rgba(255,255,255,0.10)`  
**Border radius:** 14px  
**Shadow:** large drop shadow

### Step 1 — Provider Picker

```
┌──────────────────────────────────────┐
│  Add remote connection            ✕  │
│  Select a provider to configure      │
├──────────────────────────────────────┤
│  ┌──────┐  ┌──────┐  ┌──────┐       │
│  │  ☁  │  │  ⬡  │  │  △  │       │
│  │ CW   │  │ GCP  │  │Azure │       │
│  └──────┘  └──────┘  └──────┘       │
│  ┌──────┐  ┌──────┐  ┌──────┐       │
│  │  ⌥  │  │  ◈  │  │  ▲  │       │
│  │ SSH  │  │Docker│  │Vercel│       │
│  └──────┘  └──────┘  └──────┘       │
└──────────────────────────────────────┘
```

**Header:**
- Title: "Add remote connection" — `C_TEXT`, 14px, 700
- Subtitle: "Select a provider to configure" — `C_MUTED`, 11.5px
- ✕ close button top-right

**Provider grid:** `QGridLayout`, 3 columns, 2 rows, gap 8px

**Provider card** (each provider):
- Background: `#17171f` (hover: `#1e1e2c`)
- Border: `rgba(255,255,255,0.06)` (hover: `rgba(255,255,255,0.13)`)
- Border radius: 9px
- Padding: 13px
- Icon area: 30×30 rounded rect, `provider_color + "20"` bg, `provider_color + "35"` border, font 15px, color = `provider_color`
- Name: `C_TEXT`, 12px, 600, margin-top 9px
- Description: `C_MUTED`, 10.5px, line-height 1.45

**Providers:**
| id | name | icon | color | description |
|---|---|---|---|---|
| cloudwatch | AWS CloudWatch | ☁ | #ff9900 | AWS CloudWatch Logs |
| gcp | Google Cloud | ⬡ | #4285f4 | Google Cloud Logging |
| azure | Azure Monitor | △ | #0078d4 | Azure Monitor / Log Analytics |
| ssh | SSH | ⌥ | #56cf80 | Remote log files over SSH |
| docker | Docker | ◈ | #2496ed | Remote Docker container logs |
| vercel | Vercel | ▲ | #e2e2e2 | Vercel deployment & runtime logs |

### Step 2 — Connection Form

Replaces the provider grid within the **same dialog** (use `QStackedWidget` inside the dialog).

```
┌─────────────────────────────────────┐
│  ←  ☁  AWS CloudWatch              ✕│
│      New connection                  │
├─────────────────────────────────────┤
│  CONNECTION NAME                     │
│  [prod-us-east-1              ]      │
│                                      │
│  AWS REGION                          │
│  [us-east-1                   ]      │
│                                      │
│  AWS PROFILE                         │
│  [default                     ]      │
│                                      │
│  ACCESS KEY ID                       │
│  [AKIA… (optional)            ]      │
│                                      │
│  SECRET KEY                          │
│  [••••••• (optional)          ]      │
├─────────────────────────────────────┤
│  [Cancel]          [Open] [Save & Open]│
├─────────────────────────────────────┤
│  Open — connect once without saving. │
│  Save & Open — store for later.      │
└─────────────────────────────────────┘
```

**Header:**
- Back button (←) — `_svg_icon(_SVG_CHEVRON_LEFT, C_MUTED)`, click returns to step 1
- Provider icon (22×22)
- Provider name (`C_TEXT`, 13.5px, 700) + "New connection" (`C_MUTED`, 11px) below
- ✕ close button

**Fields** — built dynamically per provider:

Field label: `C_ACCENT`, 10px, 700, uppercase, letter-spacing 0.8px  
Input: `QLineEdit`, background `C_BG`, border `rgba(255,255,255,0.10)`, border-focus `C_ACCENT + "88"`, border-radius 5px, padding 6px 10px, font monospace 11.5px, color `C_TEXT`  
Password fields: `setEchoMode(QLineEdit.EchoMode.Password)`

**Fields per provider:**

CloudWatch:
- `name` — "Connection name" — ph: "prod-us-east-1"
- `region` — "AWS Region" — ph: "us-east-1"
- `profile` — "AWS Profile" — ph: "default"
- `access_key` — "Access Key ID" — ph: "AKIA… (optional)"
- `secret_key` — "Secret Key" — type: password — ph: "••••••• (optional)"

GCP:
- `name` — "Connection name" — ph: "gcp-staging"
- `project` — "Project ID" — ph: "my-project-123"
- `credentials` — "Service account JSON path" — ph: "~/.config/gcloud/key.json"

Azure:
- `name` — "Connection name" — ph: "azure-prod"
- `workspace_id` — "Workspace ID" — ph: "xxxx-xxxx-xxxx-xxxx"
- `tenant_id` — "Tenant ID" — ph: "xxxx-xxxx-xxxx-xxxx"
- `client_id` — "Client ID" — ph: "xxxx-xxxx-xxxx-xxxx"
- `client_secret` — "Client secret" — type: password

SSH:
- `name` — "Connection name" — ph: "prod-server"
- `host` — "Host" — ph: "192.168.1.10"
- `port` — "Port" — ph: "22"
- `user` — "Username" — ph: "ubuntu"
- `key_path` — "SSH key path" — ph: "~/.ssh/id_rsa"

Docker:
- `name` — "Connection name" — ph: "docker-remote"
- `host` — "Docker host" — ph: "tcp://10.0.0.1:2376"
- `cert_path` — "TLS cert path" — ph: "/path/to/certs (optional)"

Vercel:
- `name` — "Connection name" — ph: "vercel-prod"
- `token` — "API Token" — type: password
- `team` — "Team slug" — ph: "acme-corp (optional)"

**Validation:** "Save & Open" and "Open" buttons are disabled until `name` field is non-empty.

**Footer buttons:**
- `Cancel` — `_ghost_btn("Cancel")` — closes dialog, returns `QDialog.DialogCode.Rejected`
- `Open` — `_ghost_btn("Open")` — connects without saving, returns a custom result code `RESULT_OPEN = 2`
- `Save & Open` — `_primary_btn("Save & Open")` — saves to `creds_store`, returns `QDialog.DialogCode.Accepted`

**Hint text** below buttons:
- `C_MUTED`, 10.5px
- "**Open** — connect once without saving.   **Save & Open** — store the connection for later."

---

## Screen 3 — Provider Detail View (Sidebar)

When the user clicks on a provider group header (not a connection row), the sidebar replaces `RemoteHomePanel` with `ProviderDetailWidget`.

**Class:** `ProviderDetailWidget(QWidget)`

```
┌─────────────────────────────────┐
│ ←  ☁  AWS CloudWatch       [2] │  ← Back + title + count badge
├─────────────────────────────────┤
│ [+ Add connection (dashed btn)] │
├─────────────────────────────────┤
│  ● prod-us-east-1               │
│    us-east-1                    │
│                                 │
│  ● staging-eu-west-1            │
│    eu-west-1                    │
└─────────────────────────────────┘
```

**Back button:** `_svg_icon(_SVG_CHEVRON_LEFT, C_MUTED)` — returns to `RemoteHomePanel`  
**Count badge:** `QLabel`, `C_MUTED` 10px, `rgba(255,255,255,0.05)` bg, `C_BORDER` border, border-radius 99px, padding 2px 8px  
**Add button:** dashed border `rgba(255,255,255,0.10)`, hover border `C_ACCENT + "60"`, hover color `C_ACCENT`  

**Connection rows** — same style as in `RemoteHomePanel`:
- Green dot + name (mono) + subtitle
- Hover reveals delete button with confirm flow

---

## Data Persistence

Use the existing `creds_store.py` unchanged.

**"Save & Open"** → call `creds_store.save(provider_id, data_dict)` where data_dict contains all field values.

**Loading saved connections on startup:**
```python
# In RemoteHomePanel.__init__:
for provider_id in ["cloudwatch", "gcp", "azure", "ssh", "docker", "vercel"]:
    data = creds_store.load(provider_id)
    if data:
        self._connections[provider_id].append(data)
```

**Note:** `creds_store` currently stores only ONE dict per provider name. To support multiple connections per provider, extend `creds_store` to use a list:

```python
# creds_store_v2.py (new file or extend existing)
def load_all(service: str) -> list[dict]:
    path = _DIR / f"creds_{service}.json"
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else [data]
    except (OSError, json.JSONDecodeError):
        return []

def save_all(service: str, connections: list[dict]) -> None:
    _DIR.mkdir(parents=True, exist_ok=True)
    (_DIR / f"creds_{service}.json").write_text(json.dumps(connections, indent=2))

def append_connection(service: str, conn: dict) -> None:
    conns = load_all(service)
    conns.append(conn)
    save_all(service, conns)

def delete_connection(service: str, conn_id: str) -> None:
    conns = [c for c in load_all(service) if c.get("id") != conn_id]
    save_all(service, conns)
```

Each connection dict should include a unique `"id"` field: `conn["id"] = str(uuid.uuid4())`.

---

## Interactions & Behavior

### Opening a connection ("Open" button)
After the dialog returns `RESULT_OPEN`:
- Build the provider client directly (same logic as the current individual panels: `cloudwatch.make_client(...)`, `ssh_utils.connect(...)`, etc.)
- Open a new log tab — same signal/flow as the current `open_tab` signal on each provider panel

### "Save & Open"
1. Call `creds_store_v2.append_connection(provider_id, conn_dict)`
2. Refresh `RemoteHomePanel` connection list
3. Then open the log tab (same as "Open")

### Delete confirmation (two-click)
- First click on trash → button turns red, text becomes "Confirm", color `C_ERR`
- Mouse leave → reset to default
- Second click → call `creds_store_v2.delete_connection(provider_id, conn_id)` → refresh list

### Dialog navigation
- ESC on step 2 → goes back to step 1 (not close)
- ESC on step 1 → closes dialog
- ← back button on step 2 → goes to step 1

---

## Signal Flow

```
NavRail.index_changed(0)
  → MainWindow shows RemoteHomePanel in left sidebar

RemoteHomePanel._add_btn.clicked
  → AddConnectionDialog.exec()
  → if result == RESULT_OPEN:
       MainWindow._open_remote_tab(provider_id, form_data, save=False)
  → if result == Accepted:
       creds_store_v2.append_connection(provider_id, form_data)
       RemoteHomePanel.refresh()
       MainWindow._open_remote_tab(provider_id, form_data, save=False)

RemoteHomePanel.ConnRow.delete_clicked(provider_id, conn_id)
  → creds_store_v2.delete_connection(provider_id, conn_id)
  → RemoteHomePanel.refresh()

RemoteHomePanel.ProviderGroup.header_clicked(provider_id)
  → RemoteHomePanel shows ProviderDetailWidget for that provider
```

---

## Files to Modify

| File | Change |
|---|---|
| `ui.py` | Replace remote stacked-widget contents with `RemoteHomePanel`, `AddConnectionDialog`, `ProviderDetailWidget` |
| `creds_store.py` | Add `load_all`, `save_all`, `append_connection`, `delete_connection` (multi-connection support) |
| `i18n.py` | Add keys: `remote_add`, `remote_no_connections`, `remote_open`, `remote_save_open`, `remote_confirm_delete` |

**Do not modify:** `workers.py`, `cloudwatch.py`, `gcp_utils.py`, `azure_utils.py`, `ssh_utils.py`, `docker_utils.py`, `vercel_utils.py`, `NavRail`, `FilePanel`, `FilterSearchSidebar`, `LogViewer`

---

## Reference Files

- `simplelog-remote.html` — full interactive prototype (open in browser to explore all interactions)
- `Remote Connections.html` — earlier prototype iteration (ignore, superseded)

---

## Key PyQt6 Implementation Notes

- Use `QDialog` with `QStackedWidget` for the two-step modal
- Use `QScrollArea` wrapping a `QVBoxLayout` for the connection list (same pattern as existing panels)
- Use `QFrame` with `setCursor(Qt.CursorShape.PointingHandCursor)` for clickable group rows
- Delete confirm state: store on the row widget itself, use `QTimer.singleShot` to auto-reset after 3s
- Provider icon: render with `_svg_icon()` helper (already exists in `ui.py`)
- The dashed "Add connection" button border: use stylesheet `border: 1px dashed rgba(255,255,255,26);`
- Green status dot: `QLabel` with `border-radius: 3px; background: C_INFO;` (3×3 or 5×5 fixed size)

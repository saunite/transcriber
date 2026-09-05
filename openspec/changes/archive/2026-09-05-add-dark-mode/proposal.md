## Why

The GUI currently ships one hardcoded light palette (`color-scheme: light` in `src/style.css`, no dark variant anywhere). A user running the app at night, or who simply runs their OS in dark mode, gets a bright green-white chart surface regardless — no other part of their desktop behaves that way. Theme-follows-system is a baseline expectation for a native-feeling desktop app, and a "meeting recorder" in particular is plausibly open during dim rooms or late calls where a forced-light UI is genuinely uncomfortable.

## What Changes

- **A dark palette for the existing chart-recorder GUI**, sitting alongside the current light palette rather than replacing it. The actual dark colors (pen inks, grid, panel, ink hierarchy) are a design decision, not an engineering one — produced via the impeccable skill during implementation, working from the existing light palette and direction contract (`.impeccable/surfaces/src-index-html.md`) as its starting point, not invented ad hoc in this proposal.
- **Defaults to the OS theme.** On first launch (no stored preference), the app matches the system's light/dark setting and stays in sync if the system setting changes while the app is open.
- **A manual override control**, a three-way choice (System / Light / Dark) rather than a single toggle, so "follow the system" remains selectable again after a user picks an explicit theme. The chosen preference persists across restarts.
- **Native window chrome follows the same choice.** This app uses OS-drawn window decorations (title bar), not custom ones — the title bar's own light/dark rendering should match the resolved theme (system-followed or overridden), not just the in-page content.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `desktop-gui`: adds requirements for a persisted theme preference (system/light/dark), defaulting to and live-following the system theme when unset, and the resolved theme applying to both in-page content and native window chrome.

## Impact

- **Changed**: `src/style.css` (a dark token set alongside the existing light one), `src/index.html` (a theme control, likely near existing settings), `src/main.js` (resolving system preference via `prefers-color-scheme`, persisting the user's explicit choice, listening for live system-theme changes), `src-tauri/src/main.rs` or equivalent (syncing native window chrome to the resolved theme via Tauri's window theme API).
- **Unchanged**: the sidecar CLI flag contract, all Python engine code, the IPC command/event contract with the sidecar. This is a frontend-and-window-chrome-only change.
- **Design ownership**: the dark palette itself is produced through the impeccable skill against the existing light-mode direction contract, not specified in this proposal or design.md — those documents cover the mechanism (persistence, system-following, chrome sync), not the colors.
- **Platform note**: no per-platform implementation divergence expected — `prefers-color-scheme` and Tauri's window theme API are cross-platform (Windows/Linux/macOS), so this stays a single change rather than a platform split.

## Context

See proposal.md - Why/What Changes. The frontend is plain HTML/CSS/JS with no build step (`frontendDist: ../src`, a hard product constraint carried from the `redesign-gui-chart-recorder` change). The current palette is a single set of CSS custom properties on `:root` in `src/style.css`, with `color-scheme: light` hardcoded. The app uses native OS-drawn window decorations (Tauri's default; `decorations` is not overridden in `tauri.conf.json`), so the title bar's own theme is a separate concern from in-page CSS.

Checked against `src-tauri/gen/schemas/acl-manifests.json`: `core:window`'s default permission set includes `allow-theme` (read the current theme) but **not** `allow-set-theme` — setting the window's theme requires explicitly adding `core:window:allow-set-theme` to `src-tauri/capabilities/default.json`. This is a one-line capability-file change, not a new Rust command; Tauri's window theme API is built in and already reachable from the frontend via `withGlobalTauri: true`.

## Goals / Non-Goals

**Goals:**
- Default to the OS theme, live-following it while no explicit override is set.
- Let the user pick System, Light, or Dark explicitly, persisted across restarts.
- Keep native window chrome (title bar) in sync with the resolved theme, not just in-page content.

**Non-Goals:**
- Choosing the actual dark palette (pen inks, grid, panel colors). Per the proposal, this goes through the impeccable skill against the existing light-mode direction contract at apply time — this document fixes the mechanism, not the colors.
- Any backend/Python/sidecar change. This is frontend CSS/JS plus one Tauri capability grant.
- A build step, framework, or new dependency, for the same no-build-step reason `redesign-gui-chart-recorder`'s design.md gave.

## Decisions

**Persistence via `localStorage`, not a backend setting.** This is a pure UI preference with no reason to be visible to the Python sidecar or to survive anywhere but this machine's browser storage. Reusing the browser's native mechanism needs no new dependency and no IPC round-trip. Key: a single stored value, one of `system` / `light` / `dark`; absence means `system` (first-launch default).

**System detection and live-follow via `matchMedia`, not a Tauri API.** `window.matchMedia('(prefers-color-scheme: dark)')` plus its `change` event is the standard web mechanism for both the initial read and live updates — native, zero dependencies, and it is what drives the in-page CSS regardless of which of the three preference states is active (see next decision). Tauri's own `theme()`/`onThemeChanged` window API would duplicate this for content purposes; it's reserved for the chrome-sync decision below, where it's the only option.

**Three CSS states via a `data-theme` attribute plus `prefers-color-scheme`, not a JS-driven class-per-color-swap.** `system` preference: no `data-theme` attribute is set, and a `@media (prefers-color-scheme: dark)` block (guarded so an explicit `light` override always wins) supplies the dark tokens. `light`/`dark` preference: `data-theme="light"` or `data-theme="dark"` on the root element forces that palette regardless of the OS setting, via a selector that outranks the media-query block. This is the same light/dark-token structure already used elsewhere in this environment for exactly this three-state requirement (bare `:root` for light tokens, redefined under a guarded dark media query, redefined again under an explicit `[data-theme="dark"]` selector so the manual override always wins in both directions) — proven, and it means switching preference is one attribute write, not a re-render.

**`color-scheme` follows the same resolved state.** Setting the CSS `color-scheme` property (`light`, `dark`, or `light dark` for system) alongside the token swap gets native form controls and scrollbars dark-themed by the browser engine itself, for free — no hand-styled dark variants needed for checkboxes, selects, or scrollbars beyond what the prior change already themed explicitly.

**Window chrome synced via Tauri's built-in `setTheme`, requiring one capability grant.** On every resolve (initial load, explicit user choice, or a live system-preference change while `system` is active), call the frontend's `getCurrentWindow().setTheme(theme)` with `'light'`, `'dark'`, or `null` (`null` = follow system, handled by Tauri/the OS directly, so no re-listening is needed for that case at the chrome level). This needs `core:window:allow-set-theme` added to `src-tauri/capabilities/default.json` — without it the call silently fails or errors at runtime, so this is called out explicitly as its own task rather than left implicit in "wire up the theme control."

**Control placement and the dark palette itself are deferred to implementation**, per the proposal — the mechanism above is independent of both.

## Risks / Trade-offs

- [Forgetting the `core:window:allow-set-theme` capability grant is a silent runtime failure, not a build-time error] → Mitigation: called out as its own explicit task, not folded into a larger "wire up the control" step.
- [A three-state System/Light/Dark control is more surface than a plain light/dark toggle] → Accepted deliberately, not a scope add: the proposal specifically asks to keep "follow the system" reachable again after an explicit choice, which a two-state toggle can't represent.
- [Native window chrome re-theming has no visible effect at all on Linux/GTK, confirmed during implementation (not merely speculated): `tao`'s Linux backend implements `set_theme` as `GtkSettings::set_gtk_application_prefer_dark_theme()`, a global best-effort hint, and modern GNOME drives window chrome from its own system-wide `color-scheme` setting instead, ignoring that hint entirely — pixel-verified identical title-bar color between a light and dark capture on this machine] → Accepted, not fixed: there is no better public Linux API for a genuine per-window chrome override, and forcing one via a GTK CSS override would mean fighting the user's actual desktop theme, which is worse than the current best-effort call. Recorded as its own spec scenario (not silently dropped) rather than left as an unstated gap between the written requirement and Linux's actual behavior.

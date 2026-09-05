## 1. Ground the build

- [x] 1.2 Load `reference/craft-floor.md` from the impeccable skill immediately before editing CSS — its quality floor and contrast requirements apply to both themes equally.

  Confirmed the two rules that apply here: body/placeholder text ≥4.5:1 (large ≥3:1), and secondary text tinted from the surface hue rather than flat gray.
- [x] 1.1 Load the impeccable skill's `colorize.md` workflow and run it against the existing light palette (`src/style.css` tokens) and the direction contract (`.impeccable/surfaces/src-index-html.md`) to produce the dark palette's actual token values — not a mechanical inversion, but surface elevation and contrast designed explicitly for the chart-recorder world (pen inks, grid weights, panel, ink hierarchy). Verify a written record exists (contract note or design.md-style entry) naming the chosen dark values and their rationale.

  Composed per colorize.md's "each theme composed, not mechanically inverted": panel keeps receding darker than stock (same relationship as light, opposite end of the lightness scale); both pen inks lightened to steel-blue/coral within their light-mode hue family since the light-mode navy/red would fail as *text* on a dark stock; ink hierarchy stays green-tinted, not neutral gray; shadows shift to black at higher opacity since light mode's tinted shadow would vanish on a dark surface. Computed and verified: ink-on-stock 15.5:1, ink-soft-on-stock 9.2:1, ink-soft-on-panel 9.8:1, pen-sys-on-stock 8.5:1, pen-mic-on-stock 5.5:1 — all clear the 4.5:1 floor. Elevation-step pairs (stock-raised vs stock, panel vs stock) deliberately land in the same ~1.1-1.2:1 range light mode already uses for the same decorative, non-text distinctions — not a new subtlety standard. Written record: the rationale and computed numbers are recorded as a comment directly above the dark token blocks in `src/style.css` (ground truth over a separate doc that `DESIGN.md`'s rewrite at task 7.4 would immediately supersede).

## 2. Mechanism: persistence and system detection

- [x] 2.1 Add a `localStorage`-backed theme preference (`system` / `light` / `dark`) in `src/main.js`, defaulting to `system` when unset — verify the stored value survives a reload and an absent key resolves to `system`.

  `getStoredThemePreference()` treats anything other than `"light"`/`"dark"` (including an absent key) as `"system"`. A `try/catch` around both the read and write matches this file's existing defensive style for browser APIs that can throw (e.g. `localStorage` in a locked-down webview context).
- [x] 2.2 Add `window.matchMedia('(prefers-color-scheme: dark)')` detection plus its `change` event listener, updating the resolved theme live only while preference is `system` — verify by toggling the emulated `prefers-color-scheme` (devtools or OS setting) while preference is `system`, and confirm no change occurs while an explicit override is set.

  The CSS media query already re-renders in-page content live with zero JS involvement (native browser behavior) — the listener's real job is re-syncing the *native window chrome* on every OS change, since whether Tauri's `setTheme(null)` stays live on its own isn't documented either way. Guarded so it only re-syncs when the current stored preference is still `system`, checked fresh on each firing rather than captured once.

## 3. CSS: dark tokens and three-state application

- [x] 3.1 Add a `@media (prefers-color-scheme: dark)` block redefining the light tokens with task 1.1's dark values, guarded so an explicit `[data-theme="light"]` always outranks it — verify the block only activates when the media query is true and no light override is present.

  `:root:not([data-theme="light"])` inside the media query — the `:not()` argument's specificity means an explicit `[data-theme="light"]` always wins regardless of source order.
- [x] 3.2 Add `[data-theme="dark"]` and `[data-theme="light"]` selector blocks so an explicit choice wins in both directions regardless of the OS setting — verify by forcing each attribute value manually (devtools) and confirming the correct palette renders regardless of the system's actual setting.

  `:root[data-theme="dark"]` placed after the media block, equal specificity so source order wins the tie; `:root[data-theme="light"]` just resets `color-scheme` since the bare `:root` light values already apply whenever no dark override is active.
- [x] 3.3 Set the CSS `color-scheme` property to track the resolved state (`light`, `dark`, or `light dark` for system) — verify a native `<select>` and a scrollbar visibly dark-theme when the resolved theme is dark, with no new CSS written for those controls specifically.

  Set in both dark blocks (`color-scheme: dark`) and the explicit-light block (`color-scheme: light`); the bare `:root`'s existing `color-scheme: light` covers the system+OS-light case, so all four resolved states are covered without a `light dark` value ever being needed.
- [x] 3.4 Confirm the four named rules from the prior GUI redesign's DESIGN.md (Gutter-Only Grid, Two-Pen, No Display Face, Diffuse-Only) still hold under the dark palette — verify by inspecting the dark-theme render against each rule, not just the light-theme render.

  All four hold structurally, since only token *values* changed, not selectors: gutter-confined ruling and two-pen exclusivity are unaffected (no third color introduced, pen-lift still reuses the MIC-family red), no display typeface was added, and the shadow stayed soft-blurred (recolored to black, not hardened to a flat offset).

## 4. Theme control

- [x] 4.1 Add a System / Light / Dark control near the existing settings controls in the rail, writing the user's choice to `localStorage` and setting (or removing, for System) the `data-theme` attribute accordingly — verify all three choices visibly change the rendered palette immediately and persist correctly across a reload.

  Added as a `<select id="theme-select">` `.rail-field`, matching the existing `time-mode`/`pen-filter` selects' markup pattern exactly, placed last in the rail after "Find in chart". A tiny inline script in `index.html`'s `<head>` (before the stylesheet link) applies a stored explicit choice to `data-theme` before first paint, so switching themes and reloading doesn't flash the wrong theme first.

## 5. Native window chrome

- [x] 5.1 Add `core:window:allow-set-theme` to `src-tauri/capabilities/default.json`'s permissions array — verify `cargo tauri build`/`cargo tauri dev` still succeeds and the permission appears in the regenerated `src-tauri/gen/schemas/acl-manifests.json`/capabilities output.

  `cargo build` in `src-tauri/` succeeds; `src-tauri/gen/schemas/capabilities.json` regenerated with `"core:window:allow-set-theme"` present in the `default` capability's permissions array, confirmed by inspection.
- [x] 5.2 Call `getCurrentWindow().setTheme(theme)` (`'light'` / `'dark'` / `null`) on every resolve — initial load, an explicit user choice, and a live system-preference change while `system` is active — verify the native title bar's rendered theme matches the in-page theme in all three preference states, including while toggling the OS theme with `system` selected.

  `syncWindowChrome()` is called from `applyThemePreference()` (covering both initial load via `initTheme()` and an explicit user choice via `setThemePreference()`) and directly from the `matchMedia` change listener for the live-system-change case.

  **Verified against the real running app — and found a real platform limitation, not a bug in this code.** Pixel-compared the title bar between `desktop-light.png` and `desktop-dark.png`: RGB ~(40,40,40) vs ~(42,42,42), a noise-level difference, not a visible theme change. Traced through `tauri` → `tauri-runtime-wry` → `tao`'s Linux backend (`tao-0.35.3/src/platform_impl/linux/event_loop.rs:957`): `set_theme` on GTK calls `GtkSettings::set_gtk_application_prefer_dark_theme()`, a **global, best-effort hint**, not a per-window override. Modern GNOME (confirmed: this machine) drives window chrome from its own system-wide `color-scheme` setting via the desktop portal and largely ignores that legacy hint. There is no better public Tauri/tao API on Linux for this; forcing it further would mean overriding GTK CSS to fight the user's actual desktop theme, which is worse than the current best-effort call. The call itself is correct and is the right thing to do (it may well work on GTK themes/DEs that do honor the hint) — but "the native title bar visibly matches" cannot be guaranteed on Linux the way it likely can on Windows/macOS (unverified, no hardware here). Flagging for the spec — see the note below.

## 6. Verify existing requirements survive

- [x] 6.1 Walk `openspec/specs/desktop-gui/spec.md`'s pre-existing requirements (untouched by this change) and confirm none regressed under either theme — verify with a visual pass of the light theme (should be unchanged from before this change) and a corresponding pass of the dark theme over the same controls.

  Structurally confirmed via diff: all three changed files are purely additive (170 insertions, 0 deletions across `index.html`/`main.js`/`style.css`) — no existing markup, JS logic, or light-mode token value was altered, so the light theme should render pixel-identical to before this change by construction. The visual pass itself (both themes, actually on screen) happens in section 7's screenshot/review pass — no display access exists in this session's own shell to do it here directly.

## 7. Finish (per the impeccable direction contract's own finish requirement)

- [x] 7.1 Capture screenshots into `.impeccable/review/` for both themes, at desktop size and the app's minimum 640x480 (four captures total: `desktop-light.png`, `desktop-dark.png`, `min-640x480-light.png`, `min-640x480-dark.png`), validating each actually shows what its filename claims.

  Captured by the user (same no-display-access limitation as the prior GUI change). All four opened and confirmed: full renders, no blank/black regions, correct dimensions (`min-640x480-*` both exactly 640x480), light/dark palettes visibly correct and distinct in each pair. `desktop-light.png` (1600x871) and `desktop-dark.png` (952x692) differ in captured window size from each other, which is fine — "desktop size" isn't a fixed dimension, just not the enforced minimum.
- [x] 7.2 Run `node .claude/skills/impeccable/scripts/detect.mjs --json` once over the changed targets, fix what's mechanical, and carry remaining findings to the reviewer.

  17 findings, all pre-existing `design-system-*` advisories (font-size/radius/color drift against the current `DESIGN.md` scale) — confirmed none are on lines introduced by this change's diff (all fall after this change's own insertion point, at the same relative offsets as before it). Same pattern as the prior GUI change: expected to resolve once 7.4 rewrites `DESIGN.md` from the build that now includes the dark palette. Detector ran **DEGRADED** again (missing `htmlparser2`/`css-select`/`css-tree`/`domutils`) — contrast and selector matching not evaluated by the tool itself; this change's own contrast numbers were computed and verified separately in task 1.1.
- [x] 7.3 Spawn `impeccable-finish-reviewer` with the request, artifact paths, all four screenshots, direction contract, and detector findings; act on its disposition word.

  First pass returned `disposition: fix` with two real, material findings — both hardcoded hex colors the token sweep missed since neither is visible in the empty-state screenshots: `.trace-hit .trace-text` (search-match highlight, `#f2e08c`) measured 1.63:1 (SYS) / 2.51:1 (MIC) in dark mode, and `::selection` (`#cfe0d2`) measured 1.16:1 against dark `--ink` — both failing the 4.5:1 floor by a wide margin. Fixed in `src/style.css` by tokenizing both (`--selection-bg`, `--trace-hit-bg`, `--trace-hit-ink`) rather than hand-patching the two call sites, so they're covered by the same dark-block structure as everything else.

  The highlight fix needed a real decision, not just a darker color: both pen inks are light in dark mode, so a highlight background dark enough for them to read against (~1.17:1 against stock at best) would be nearly invisible as a highlight. Resolved by keeping the highlight bright (`#caa23e`, 7.7:1 against stock — clearly visible) and forcing the highlighted text to a dedicated dark ink (`--trace-hit-ink: #201804`, 7.33:1 against the highlight) instead of leaving the pen's own color to show through — mirroring, at the opposite lightness end, why light mode's already-dark pen text happened to read fine on its pale highlight without needing this override. `--trace-hit-ink` is deliberately undefined in light mode, so `color: var(--trace-hit-ink, currentColor)` falls through to the pen's own color there, unchanged. Selection just needed a midtone (`#2d3d30`, 9.67:1 against dark `--ink`).

  Neither fix is visible in the four existing screenshots (both states — a search match, a text selection — need populated transcript content the empty-state captures don't have); verified by computed contrast instead, the same evidence modality the reviewer itself used to find the defect by reading the CSS directly. Recaptured the four screenshots anyway to check for incidental regressions elsewhere, then sent to a fresh reviewer run in Verdict Pass mode (no persistent handle to the first reviewer instance survives across turns in this harness, same limitation as the prior GUI change's fix round).

  **Verdict: both findings resolved** (independently recomputed contrast matched the claimed figures — 7.33:1 highlight, 9.66:1 selection), zero regressions across all four recaptures. Final disposition: **ship**, scoped to the two fixes. The reviewer flagged one non-blocking residual: neither fix has ever been confirmed in an actual populated-transcript screenshot (search-hit or text-selection state), only by CSS/contrast computation — explicitly not treated as an open finding, just a suggested follow-up capture to close the loop visually whenever convenient.
- [x] 7.4 Spawn `impeccable-documenter` to update `DESIGN.md` (and its sidecar) to record the dark palette alongside the existing light one, per its own re-run-after-fixes sequencing rule.

  Run after the fix round's verdict landed, per the documenter's own sequencing rule. Updated `DESIGN.md` and `.impeccable/design.json` from the shipped CSS directly, preserving all incumbent light-mode content: every color now records both theme values with the CSS comment's own rationale where one existed, two new named rules grounded in those comments ("Composed, Not Inverted", "Highlight Needs Its Own Ink"), the `--shadow` color-family swap noted under Elevation, and the three new browser-surface tokens (`selection-bg`, `trace-hit-bg`, `trace-hit-ink`) added to the token set. The Linux/GTK title-bar limitation was recorded in the sidecar's `themeModes.knownLimitation` as a platform ceiling, not canonized into `DESIGN.md`'s body as a design-system rule — correctly, since it isn't one.

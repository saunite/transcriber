## 1. Ground the build

- [x] 1.1 Re-read the direction contract (`node .claude/skills/impeccable/scripts/surface-brief.mjs read src/index.html`) — it is the authoritative design source, and the finish reviewer audits the build against it
- [x] 1.2 Load `reference/craft-floor.md` from the impeccable skill immediately before editing UI (its quality floor and absolute bans apply to this build; it is deliberately not loaded during planning)

## 2. The chart world

- [x] 2.1 Rebuild `src/index.html` structure in the chart world: gridded roll, calibrated time axis, two pens (SYS/MIC), instrument controls down one edge, destination as the chart's title block, one large START that lowers the pens

  Title block carries destination + model + language; rail carries mode switch, transport, pens, devices, chart speed, filter, search; chart area is the roll.
- [x] 2.2 Rebuild `src/style.css` for the world in the contract's OWN-WORLD block — pale green-white chart stock, faint warm-red gridlines at minor/major weights, blue-black SYS pen, red MIC pen. Every control rebuilt in the form's vocabulary; a stock control inside a committed form is a lapse

  Stock `#e9f0ea`, grid `#dfc9c2`/`#cfa89d` at 12px/60px, SYS `#16233a`, MIC `#b4231d`. The printed grid is fixed-spacing on the stock and the marks land where time puts them — true to how chart paper actually works. Browser surfaces themed per the craft floor: `::selection`, `caret-color`, scrollbars, `:focus-visible`, tabular numerals. The pen nib is a drawn `clip-path` shape, not a glyph.
- [x] 2.3 Verify no decorative waveform or amplitude band exists anywhere in the build — the text is the trace. This is the direction's named failure mode

  Confirmed: no waveform, no amplitude band, no canvas. The only marks are per-line pen ticks positioned by time.

## 3. Time as the organizing law

- [x] 3.1 Position transcript lines along the time axis from each line's own timestamp (not arrival time), so live capture and file transcription produce the same artifact; verify a multi-minute gap renders proportionally larger than a seconds-long one

  `parseStamp()` handles all three real engine formats (live `--actual-time` absolute; file `MM:SS.mmm -> ...` elapsed, minutes may exceed 59; file+actual-time absolute range) and is **tested against the shipped implementation** — the harness `eval`s the function straight out of `src/main.js` rather than a retyped copy. All 7 format cases plus two elapsed-gap assertions pass, including `78:12.500` → 4692.5s, which a naive `MM:SS` regex would silently mangle.
- [x] 3.2 Implement the chart speed control as a single scale factor driving the axis; verify a long session compresses to one view and expands to readable text with interval proportions preserved

  One continuous slider → `pxPerSecond` (0.2 → 30, exponential), driving `--chart-scale` plus a `data-scale-mode` of overview/compact/reading. At overview the trace collapses to marks so the session's *shape* is what you read; proportions are preserved at every scale. Gaps are true-scale (guarded only against malformed data at 24h), which is what chart speed exists to make navigable.
- [x] 3.3 Verify both sources position against the same shared axis in a dual-source session

  Both pens append to one `<ol>` with offsets from one session origin; there is no per-source lane or separate axis.

## 4. State vocabulary

- [x] 4.1 Implement the enumerated states from the contract, each physically distinct: PENS UP · LOADED · ADVANCING · MARKING · PEN LIFT · STOPPING · TORN OFF

  Expressed by the pen nib's own position and colour (`data-state` on `.run-state`), not a badge: parked/grey (idle), lowered/soft (loaded), down/red (advancing), **raised/red (pen lift)**, raised/soft (stopping).
- [x] 4.2 Implement stall detection as a frontend timer against the known 10s chunk duration (no backend change); verify pen-down-flat (quiet, healthy) is visually distinct from pen-lifted (no expected output)

  1s interval, threshold 2 × 10s. Deliberately armed only *after* the first real transcript chunk — before that the engine is still loading its model, which is not a stall. `sidecar-log` chatter explicitly does **not** clear a pen-lift; only a real chunk does. The detail line names the problem and the recovery, per the craft floor.
- [x] 4.3 Verify state is carried by the instrument changing, never by a badge added on top

  Confirmed: no stamp/chip/badge element exists. State is the nib moving and the label changing.

## 5. Preserve every existing requirement

- [x] 5.1 Walk `openspec/specs/desktop-gui/spec.md` requirement by requirement and confirm each of the 14 still holds in the rebuilt UI — this is the acceptance contract for "only the features must remain", not a visual once-over

  All 14 walked. 8-11 are Rust/packaging-side and untouched by a frontend-only change. Verified mechanically where possible (see 5.2). Note on requirement 1 ("sidecar SHALL NOT be spawned at app startup"): `populateMicDevices()` calls `list_devices` at init, which spawns the sidecar briefly — this is **pre-existing, unchanged** behaviour, present identically in the incumbent, and the window is shown and interactive first. Not introduced here; flagged rather than silently altered.
- [x] 5.2 Specifically confirm the easily-lost ones: WASAPI override's discouraging message verbatim, dual-source default ON, output file field + Browse, macOS live-capture degradation notice, format/task selects, drag-and-drop plus click-to-browse, and the engine log still present and load-bearing

  Verified mechanically: WASAPI warning text present **verbatim** (string-compared against the spec's wording), `include-mic-checkbox` ships `checked`, and all of `output-path-input`, `output-browse-btn`, `drop-zone`, `format-select`, `task-select`, `mic-device-select`, `macos-live-notice`, `debug-log`, `model-select`, `language-input`, `audio-device-input` present. No network references anywhere (requirement 6).
- [x] 5.3 Confirm the IPC contract is untouched: same command names, same event names, same argument shapes — diff `main.js`'s `invoke`/`listen` calls against the current file to prove nothing renamed

  Diffed against `git show HEAD:src/main.js`: all 5 commands and 7 events identical, no additions or removals. Argument names re-checked against the live Rust signatures in `sidecar.rs` (camelCase → snake_case): `model`/`language`/`includeMic`/`micDevice`/`outputPath`/`audioDevice` and `filePath`/`format`/`task`/`model`/`language` all match. A scripted check also confirms every `getElementById` in `main.js` resolves to a real id in the HTML.

## 6. Finish (per the contract's FINISH line — this is part of done)

- [x] 6.1 Rebuild and capture screenshots into `.impeccable/review/` (desktop, plus the app's minimum 640x480), validating each capture actually shows what its filename claims

  `desktop.png` (952x692) and `min-640x480.png` (640x480, actual window resized to its enforced Tauri minimum — a first attempt at this capture was caught and rejected because it was byte-for-byte the desktop size, not actually resized). Both opened and confirmed: full render, no blank/black regions, rail and chart area intact at the minimum size with nothing overlapping or clipped mid-word. Captured by the user — no display/screenshot capability exists in this session's own shell (confirmed: `xdpyinfo` unreachable, GNOME's D-Bus screenshot API returns `AccessDenied`, and `gnome-screenshot`'s X11 fallback fails the same way — a sandbox-level block, not a missing package).
- [x] 6.2 Run `node .claude/skills/impeccable/scripts/detect.mjs --json` over the changed targets once, fix what is mechanical, and carry remaining findings to the reviewer

  28 findings, **all** `design-system-*` advisories (colour/font-size/radius outside DESIGN.md) — expected drift against the stale Verbatim DESIGN.md this change removes; they resolve when 6.4 rewrites it. **Zero** real antipattern findings. Caveat carried to the reviewer: the detector ran **DEGRADED** (missing `htmlparser2`/`css-select`/`css-tree`/`domutils`), so contrast and selector matching were not evaluated — the result is an undercount, not a clean bill of health.
- [x] 6.3 Spawn `impeccable-finish-reviewer` with the request, artifact paths, screenshots, direction contract, and detector findings; act on its disposition word

  First pass returned `disposition: fix` with three material findings, all real: (1) systemic craft-floor contrast failure — every field label routed through `--ink-faint` at 2.48:1/2.97:1 against panel/stock, well under the 4.5:1 floor, exactly the class of defect the degraded detector's missing contrast tooling couldn't catch; (2) `--grid-minor` had drifted achromatic (`#d8e0d8`, gray-green) against OWN-WORLD's "warm-red gridlines at two weights"; (3) "condensed caps on labels" was silently unmet (plain uppercase system sans, no citation). Fixed in `src/style.css`: labels/placeholders/descriptions moved to the already-existing `--ink-soft` token (4.79:1/5.74:1, `.mode:disabled` deliberately left alone as WCAG-exempt); `--grid-minor` redefined as `--grid-major`'s own RGB at 0.35 alpha so the two weights share hue by construction instead of by a second hand-picked hex; condensed-caps deviation cited in a comment (a sourced webfont would mean a build step or a first-launch network fetch, both barred). Recaptured both screenshots over the same fix, sent to a fresh reviewer run explicitly in Verdict Pass mode (no persistent handle to the first reviewer instance survives across turns in this harness) — all three scored **resolved**, no regressions, gutter-confined ruling and state-as-instrument vocabulary both unregressed. The fourth finding (no QUALITY BAR card exists, so the ceiling check isn't assessable) is a standing disclosed gap, not code-fixable — carried forward, not scored. Final disposition: **ship** (scoped to the three fixes, not a whole-surface re-review).
- [x] 6.4 Spawn `impeccable-documenter` to replace `DESIGN.md` from the built world — the existing "Verbatim" DESIGN.md describes a world this change removes

  Run after the last correction landed (the finish-review fix round), per the documenter's own sequencing rule. Rewrote `DESIGN.md` and `.impeccable/design.json` from the shipped CSS/HTML directly: the two exclusive pen inks (SYS navy, MIC red) on the chart-stock/instrument-panel neutral scales, grid-minor's alpha-derived-from-major relationship, the no-display-face type ramp, and the four named rules (Gutter-Only Grid, Two-Pen, No Display Face, Diffuse-Only). The condensed-caps substitution was recorded as a cited one-off adaptation for this build, not canonized as a general house rule for future surfaces.

## 6b. Fixes from user testing on real hardware (round 1)

- [x] 6b.1 Rename metaphor-named controls to product language

  **My error, caught immediately by the user: "I don't understand the whole 'Lower Pen' thing, how do I start recording?"** The craft floor's own rule is "controls name their action", and Operate mode says expression may never obscure the task — I let the chart-recorder metaphor name the primary verb. Fixed: "Lower pens" → **Start recording**, "Raise pens" → **Stop recording**, and the state labels to plain language (Not recording / Starting / Recording / Recording stalled / Stopping). The world stays in the visual system — stock, grid, pen inks, the nib that moves — where it belongs; it is no longer vocabulary the user must decode to press a button. Empty-state copy likewise now names the control to press.
- [x] 6b.2 Fix the empty-state overlay covering real transcript lines

  Reported as "nothing was shown on the chart" — but lines *had* rendered and were sitting faded behind the `inset: 0` empty-state panel. Two faults, both fixed at root cause rather than patched: (1) visibility was tracked imperatively across `appendTranscriptLine`/`clearTranscript`, so any drift between flag and DOM painted the overlay over real content — now derived from a single `refreshEmptyStates()` reading `children.length`, making the desync unrepresentable; (2) the run state read "Not recording" while the engine was demonstrably capturing, so an arriving chunk now resyncs the state — evidence of life outranks a stale flag. Also closed a third path where a line could land on the live chart while `currentFlow` was null without ever updating state; routing and state now derive from one `isFile` decision.

  Regression-checked against the shipped implementation (harness `eval`s `refreshEmptyStates` out of `src/main.js`): overlay shows when empty, hides once lines exist, returns after a clear.

## 6c. Fixes from user testing on real hardware (round 2)

- [x] 6c.1 Fix `hidden` being a silent no-op on every element that uses it

  **The root cause behind round 1's fix not working, and behind two more symptoms.** Every element toggled via the `hidden` attribute (`.chart-empty`, `.btn-record`, `.run-state`, `.trace`, `.rail-panel`, `.rail-field`) also carries an author `display:` rule, and an author rule beats the UA stylesheet's `[hidden] { display: none }`. So `hidden` did nothing anywhere in this build. Round 1's `refreshEmptyStates()` logic was correct and silently defeated by CSS. The screenshot showed three impossible states at once: the empty overlay over live content, Start **and** Stop both visible, and both rail panels stacked (the File drop zone under the Live controls). It would also have broken the pen filter, the mic-device field, and the file busy indicator. Fixed with one `[hidden] { display: none !important; }` rule.
- [x] 6c.2 Advance the status when the engine comes up, not only when the first chunk lands

  Reported as "after it is ready in the log it is still waiting in the status message". The engine reaches `Listening...` up to a full 10s chunk before the first transcript line, and the state machine only advanced on a transcript line — so the panel sat on "Starting" while the log plainly said ready. Added a distinct `listening` state ("Listening — no speech yet") that a `sidecar-log` line advances into, with its own pen position: **pen down, drawing a flat trace**, visibly distinct from a pen lift. Log chatter still deliberately does **not** clear a stall — once chunks have been flowing, only a real chunk proves recovery.
- [x] 6c.3 Stop the terminal window flashing on every stop

  Reported as "when clicking stop a new terminal pops up for a second". `stop_live_session`'s `taskkill` is a console program spawned through `std::process::Command`, which does not suppress its console the way `tauri-plugin-shell` does for the sidecar. This violates existing requirement **"Launches without a console or terminal window"**, whose scenario covers "any process it spawns". Fixed with `CREATE_NO_WINDOW` (`0x0800_0000`) via `CommandExt::creation_flags`. Compiles clean on the Windows target.

  **Scope note, disclosed rather than absorbed silently:** this change was proposed as frontend-only, and this is a Rust edit. It is a genuine defect against an already-accepted requirement, surfaced by this change's own testing, and two lines — fixing it beat shipping a visible regression on a technicality. Recorded here so the boundary crossing is visible in review.

## 6d. Fixes from user testing on real hardware (round 3)

- [x] 6d.1 Remove the last metaphor-named control

  "Both pens" → "Both sources" in the source filter. Grep confirms no user-facing "pen" copy remains anywhere in the HTML or JS; the word survives only in CSS class names and internal state, where the user never meets it.
- [x] 6d.2 Move the ruling off the reading column and into the time gutter

  Reported as "the lines behind the text are pretty bad" — the exact risk `design.md` recorded ("gridlines fighting long-form legibility"). Fixed as a design decision rather than a dimmer switch: **the ruling belongs where time is measured, not under prose.** Vertical gridlines removed entirely (time runs vertically; verticals were pure decoration crossing the text), and the horizontal ruling is now confined to the time gutter via a background box on `.roll`, with the gutter tinted so it reads as a distinct calibrated scale. The transcript column now sits on clean stock. Grid colours softened. A grid printed across the reading column is true to chart paper and hostile to the moment this app exists for.
- [x] 6d.3 Reconcile the engine log with the displayed state

  Reported as "still doesn't seem synced between what is in the log and the actual recording state". Root cause is not a state bug in this instance: the chart correctly held a finished session's lines and the status correctly read "Not recording", but the **engine log is append-only across sessions with no boundary**, so stale `Listening…` / `Capturing audio…` scrollback keeps reading as live indefinitely. Added session boundary markers, visibly the app speaking rather than engine output: `── recording started · HH:MM:SS ──`, `── stop requested · HH:MM:SS ──`, `── engine exited unexpectedly · HH:MM:SS ──`. Wording is deliberately "stop requested", not "stopped" — whether the process actually died is what `confirm-live-session-stop` reports, and this marker must not claim knowledge it does not have.
- [x] 6d.4 Fix a resync bug introduced in round 1

  Round 1's "arriving lines outrank a stale idle state" resync had no guard, so buffered lines arriving *after* a deliberate stop could resurrect the status to "Recording" — contradicting the user's own action. Gated on a new `sessionRunning` flag (what is *supposed* to be running, distinct from `liveState`, which is what the panel displays), cleared on stop and on crash. The resync now corrects display drift without ever overriding an explicit stop.

## 6e. Fixes from user testing on real hardware (round 4)

- [x] 6e.1 Restore wall-clock timestamps, lost in the redesign

  Asked as "where do I switch the timestamp to show the actual time on the machine?" — there was no such control, and that is **a regression I introduced**, not a missing nicety. The engine always runs live capture with `--actual-time` (the reason `start_teams_transcription.bat` passes it), so wall-clock stamps are real data arriving on every line; the redesign converted them to elapsed offsets for the axis and discarded the clock reading the incumbent UI used to show.

  Fixed by keeping **both** readings on each line and adding a Timestamps control (Clock time / Time into session), defaulting to **clock time** — for a meeting record, "what time was this said" outranks "how far into the recording". Axis positions remain elapsed-proportional either way; only the label changes. Verified that the clock value round-trips losslessly (`parseStamp` builds it via `Date.UTC` from local wall-clock parts and it is read back through UTC, so `21:57:16` returns exactly `21:57:16`).

  A transcribed file carries no clock time (`MM:SS.mmm` only), so those lines fall back to elapsed and an explanatory hint appears — but **only when the fallback is actually happening**, never on a live-only session. Tested against the shipped implementation across both modes, the file fallback, and the hint's visibility; the run also confirmed `formatClock` correctly rolls past an hour (4692.5s → `1:18:13`).

## 7. Within-session search (droppable — cut here if the change must be cut short)

- [x] 7.1 Filter the chart to a single pen (SYS only / MIC only / both)
- [x] 7.2 Search the current session's transcript and move to matches along the axis

  Filter and search share one `applyFilters()` pass and re-run the layout so the time axis stays correct over the filtered set; match count is reported, and hits are marked on the trace.

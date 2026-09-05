## Why

The current GUI's design direction ("Verbatim" — a court-reporter transcript, documented in `.impeccable/surfaces/src-index-html.md`) was built around a scene that does not happen. Its own STORY block reads: *"pressing Start stamps LIVE and text appears line by line in the margin-tagged format as it's spoken"* — a hero moment spent on watching the transcript arrive. Confirmed with the user during design exploration: **the window is minimized behind the meeting during capture, and the moment that matters is reading the transcript afterward.** The incumbent optimized for an unwatched screen.

Two concrete consequences fall out of that, beyond aesthetics:

- A chat-style transcript **deletes time**. A six-minute stretch where nobody spoke renders identically to a six-second one. For a meeting record — where "where was the quiet screen-share, where was the dense argument" is real navigational information — that's lost data.
- "Capture is working, nobody is speaking" and "the capture engine has stalled" are currently **indistinguishable**. That is not hypothetical: it cost real diagnosis time during this project's own Windows hardware testing.

## What Changes

Replaces the GUI's visual world and the live/reading experience. The direction was selected through the impeccable skill's direction round (seed `4c8578ba`, `--kind pick`, code-led build path) and is recorded in full as a development contract in `.impeccable/surfaces/src-index-html.md` — that brief, not this proposal, is the authoritative design source.

- **New visual world: the chart recorder.** Two pens (SYS, MIC) sharing one calibrated time axis on gridded chart stock. The transcript text *is* the pen trace — there is no decorative waveform anywhere, which is the specific cliché this direction must refuse.
- **Silence rendered at true scale.** Gaps between transcript lines occupy proportional space on the time axis, so the shape of a session is legible before reading a word.
- **Chart speed control.** One control continuously rescales the time axis — a whole meeting compressed to a glance, down to full reading scale — without distorting time. This is what makes true-scale silence survivable on a 60-minute session; it is not separable from the point above.
- **A stalled capture becomes visibly distinct from a quiet one.** Pen down with a flat trace (working, nobody speaking) versus pen lifted (the engine stopped producing). Driven by real data: time since the last `transcript-line` event against the known 10s chunk duration.
- **Within-session search/filter** over the current chart (filter to one pen, find a passage). Purely additive and independently droppable — the last task group.

**All 14 existing `desktop-gui` requirements are preserved unchanged.** The user's constraint was "only the features must remain, not any particular screen, color or theme choice"; the existing spec is the authoritative list of what "the features" means, and it is this change's acceptance contract. Nothing in it is modified or removed — including the WASAPI override's discouraging message, dual-source-by-default, the output file field, macOS degradation, and the engine log.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `desktop-gui`: adds three requirements — time rendered at true scale, a time-scale control, and stalled-versus-silent distinguishability. No existing requirement text changes; the redesign re-expresses them, and re-expression is implementation, not spec.

## Impact

- **Rewritten**: `src/index.html`, `src/style.css`, `src/main.js` (presentation only — `main.js` keeps its existing IPC contract exactly).
- **Unchanged, and must stay unchanged**: every Rust command and event name (`start_live_session`, `stop_live_session`, `start_file_transcription`, `list_devices`, `get_platform`; `transcript-line`, `sidecar-log`, `file-transcription-complete`), the sidecar CLI flag contract, and all Python engine code. This is a frontend-only change.
- **Replaced at finish**: `DESIGN.md` — written from the built world by the impeccable documenter, per the direction contract's FINISH line. The existing "Verbatim" DESIGN.md describes a world this change removes.
- **Backend constraint carried, not silently promised**: the event contract exposes no audio levels, so pen movement is driven by chunk-arrival cadence, not amplitude. A true level meter would need a new backend event and is explicitly out of scope.
- **Out of scope**: cross-session history (reopening a previous meeting's transcript) — no session store exists; that is backend work.
- **Coordination**: `confirm-live-session-stop` (active) touches `stop_live_session` in Rust and is compatible — different layer. Apply order does not matter, but if that change lands first its new stop confirmation should appear in this design's engine log surface.

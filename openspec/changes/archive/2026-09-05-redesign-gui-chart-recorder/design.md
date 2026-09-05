## Context

See proposal.md - Why. The design direction is recorded in full at `.impeccable/surfaces/src-index-html.md` (seed `4c8578ba`, code-led) — **that brief is the authoritative design source**, and it is deliberately not duplicated here. It carries the six-block direction contract, the enumerated state vocabulary, the signature interaction, and the backend constraints. This document covers only the decisions that shape *implementation*.

The frontend is plain HTML/CSS/JS with no build step, served from `src/` via `frontendDist`. `main.js` owns presentation only; the IPC contract (commands and events) is fixed by `src-tauri/src/{main,sidecar}.rs`.

## Goals / Non-Goals

**Goals:**
- Replace the visual world and the live/reading experience while preserving all 14 existing `desktop-gui` requirements exactly.
- Make the shape of a session legible before reading it, and make a stalled engine visibly different from a quiet room.

**Non-Goals:**
- Any change to Rust commands, event names, the sidecar CLI flag contract, or Python engine code. Frontend only.
- Audio-level metering (no level events exist — see proposal Impact).
- Cross-session history (no session store exists).
- Adding a build step, framework, or dependency. The no-build-step constraint is a hard product constraint, not an incidental one.

## Decisions

**Time position is derived from timestamps already in the transcript lines, not from wall-clock arrival.** Lines already carry a timestamp (the `--actual-time` wall-clock stamp the GUI always passes). Positioning from the line's own stamp rather than from when the event happened to reach the frontend keeps file transcription — where all lines arrive at once — on the same axis as live capture, so both flows produce the same artifact. Alternative considered: measuring arrival time in the renderer; rejected because it makes file transcription's axis meaningless.

**Stall detection is a frontend timer against a known constant, not a new backend signal.** The GUI always passes `--chunk-duration 10`, so "substantially longer than expected" is a knowable threshold in the renderer (a multiple of 10s since the last `transcript-line`). No new event, no Rust change, no coordination with the sidecar. This keeps the change frontend-only, which is the whole point of its scope. Alternative considered: a heartbeat event from the sidecar; rejected as backend scope for information the frontend can already derive.

**Chart speed rescales spacing, not font size alone.** The control's job is the time axis; text legibility follows from it. Implemented as a single scale factor (CSS custom property) driving the axis, so one control moves the whole system coherently rather than three independent zoom behaviors.

**The engine log stays, and stays load-bearing.** It is not debug decoration — it is how the model-path bug, the buffering question, and the stall symptom were all actually diagnosed in this project. The redesign re-expresses it in the new world; it does not demote or hide it.

**Search is the last task group and is droppable.** Everything before it produces a coherent, shippable result. Search adds reach without which the direction still holds — so if the change needs to be cut short, it cuts there cleanly rather than leaving a broken intermediate.

## Risks / Trade-offs

- [The direction's own named failure mode: drifting into a decorative waveform band above a conventional chat list, which is the exact cliché it refuses] → Mitigation: the contract states it explicitly ("No waveform: text is the trace"), and the finish reviewer audits the build against the contract. If an amplitude band appears anywhere, the direction failed.
- [Gridlines fighting long-form legibility — chart paper's grid is genuinely noisy, and reading afterward is the primary moment] → Mitigation: the grid must stay subordinate to the trace; major (labelled) and minor (very faint) weights, with the text always the highest-contrast element on the surface.
- [True-scale silence makes a long, sparse session very tall] → Mitigated by design, not accepted: chart speed exists precisely for this, which is why the two ship together.
- [A full GUI rewrite risks silently dropping one of the 14 preserved requirements] → Mitigation: task group 5 walks the existing spec requirement by requirement rather than trusting a visual once-over.
- [`DESIGN.md` will describe a world that no longer exists until the documenter runs at finish] → Accepted and sequenced: the direction contract's FINISH line makes documentation part of done, not a follow-up.

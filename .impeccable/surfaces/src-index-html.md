---
version: 1
slug: "src-index-html"
primary_target: "src/index.html"
related_targets: ["src/main.js","src/style.css"]
---

## Scope

Operate surface. The whole app: live capture, file transcription, settings, engine log.

Scene (confirmed with the user, and it overturned the previous direction): the window is **minimized behind the meeting** during capture — nobody watches the transcript arrive. The moment that matters is **reading it afterward**. Guardrail: nothing that reads as a toy; this runs during real work.

Consequence: the incumbent "Verbatim" direction spent its entire hero moment (text appearing line by line as spoken) on a screen no one is looking at.

## Direction contract

THESIS: A chart, not a chat: two pens on one calibrated axis where silence occupies real space. Refuses the chat log, which deletes time, and the decorative waveform.

OWN-WORLD: Pale green-white chart stock, faint warm-red gridlines at two weights, two pen inks — blue-black SYS, red MIC. Tabular mono for the scale, plain face for the trace, condensed caps on labels. No waveform: text is the trace.

STORY: User fills the title block, lowers the pens, minimizes. The roll advances unattended. Glancing back, it has moved and marks are landing — or the pen lifted, reading as broken, not quiet. Stopping tears off a readable record.

FIRST VIEWPORT: Gridded roll loaded, axis drawn, pens parked at zero; controls down one edge (chart speed, SYS/MIC pens, model, language); destination as title block; one large START lowering the pens.

FORM: candidate 1 of the grounded list (chart recorder / seismograph drum), IMPECCABLE'S PICK, chosen over the assigned Field Recorder. Seed key: 4c8578ba.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.

## Signature interaction

**Chart speed.** One control rescales the time axis continuously — whole meeting compressed to a single glance (its shape: where the dense argument sat, where the six-minute silence sat) down to full reading scale. Time is never distorted; only the scale changes. This is the form's native control solving the product's real problem, and it is what makes "silence at true scale" survivable on a 60-minute session.

## State vocabulary

Enumerated, each physically distinct, none implied: PENS UP (idle) · LOADED · ADVANCING · MARKING (chunk arrived) · **PEN LIFT** (stalled — advancing expected, no chunk in >2x chunk-duration) · STOPPING · TORN OFF (readable record).

The pen-down-flat vs pen-up distinction is the point: "working, nobody is speaking" and "the instrument stalled" were indistinguishable in the incumbent, and that was a real bug class in testing.

## Constraints carried from the backend

The event contract is fixed (`transcript-line`, `sidecar-log`, `file-transcription-complete`) and carries **no audio levels**. Meters/pens are therefore driven by real chunk-arrival cadence, not amplitude. A true level meter needs a new backend event and is a named future cost, never a silent promise.

## Unresolved

Cross-session history (reopening last week's meeting) would need backend work — no session store exists. Within one session, search/filter/scan over the current chart is pure frontend and is in scope.

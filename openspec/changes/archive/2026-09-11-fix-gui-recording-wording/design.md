## Context

See proposal.md - Why. Where the strings live:

- `src/index.html`: the title-block label (line ~34), the transport buttons (~69–73), the status label (~78), and the live chart's empty state (~206–207).
- `src/main.js`: the `STATE_LABEL` table (~573–579), which drives the status line for every live state, and one `appendLogMarker("recording started")` call (~674).
- `DESIGN.md`: one line in the button section quoting the primary button's label.

The file-side strings sit in the same files ("Drop recordings", "No recording loaded") but describe dropped media, so a blind find-and-replace would be wrong.

## Goals / Non-Goals

**Goals:**
- Every user-visible mention of recording *in the live-capture flow* names transcribing instead.

**Non-Goals:**
- Renaming CSS classes, design tokens, or the chart-recorder visual metaphor.
- Touching file-side wording, where "recording" means the dropped media file.
- Any behavior change: the same states, the same transitions, the same files.

## Decisions

### 1. Replace the strings by hand, not with a global find-and-replace

There are 8 user-visible strings across 3 files, and the same files hold "recording" strings that must stay. Each is replaced individually, and task 1.4 greps for leftovers with the file-side strings excluded, so nothing is missed and nothing extra is caught.

### 2. "Transcribing" for the states, "Save to" for the field

The user picked both. "Transcribing" is the same verb the File panel's status already uses (`Transcribing <name> (n of m)`), so the two flows now read alike. "Save to" is short enough for the title block's one-line field row, where "Save transcript to" would crowd the path input.

The other `STATE_LABEL` entries are already free of the metaphor ("Starting — waiting for the engine", "Listening — no speech yet", "Stopping") and stay as they are.

### 3. No spec delta

No requirement quotes these labels. `desktop-gui`'s "A stalled capture is distinguishable from a silent one" describes the two states without naming their text, and its live-transcript and save requirements are about behavior. So the change is `skip_specs` — a spec edit would only restate the UI copy.

## Risks / Trade-offs

- **[Trade-off]** The button label grows from "Start recording" to "Start transcribing" (two characters). The transport row sizes to its content, so the layout absorbs it; task 1.5 confirms it in the running GUI rather than assuming.
- **[Risk]** A leftover "recording" string in the live flow → the grep in task 1.4 lists every remaining match with its context, so anything left is a deliberate file-side string.

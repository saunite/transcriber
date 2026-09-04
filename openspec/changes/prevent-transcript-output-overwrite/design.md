## Context

See proposal.md - Why. Two separate output-naming code paths (`src/main.js`'s output field for live sessions, `transcriber.py`'s auto-derived name for file mode) shared the same underlying gap: a filename computed once, then reused verbatim across runs.

## Goals / Non-Goals

**Goals:**
- A user can start a second live session, or re-transcribe the same file, without ever losing the previous run's transcript to a silent overwrite.
- No new Tauri permission surface, no new dependency.

**Non-Goals:**
- Detecting an actual collision and asking the user to confirm/rename (would need a filesystem-existence check, which needs the fs plugin — not registered in `capabilities/default.json` today, and adding it is a real permission-surface decision, not a corollary of this fix).
- Protecting a user-typed exact path that happens to already exist on disk for some reason *other* than this app's own repeat runs (e.g. a real file with that exact stamped name, hand-placed there seconds earlier) — out of scope; the stamp only defends against this app overwriting its own prior output.

## Decisions

**Prevent, don't detect.** Rather than checking whether the resolved path exists before writing (which would require the fs plugin, a new capability grant, and an async round-trip before every start), every run is stamped fresh with a second-resolution timestamp at the moment it actually starts. Collision becomes structurally near-impossible rather than actively caught.

**Strip a prior auto-stamp before re-stamping (live mode only).** `withFreshTimestamp()` regexes off a trailing `_YYYYMMDD_HHMMSS` before appending a new one, so starting the same already-stamped field twice in a row appends exactly one fresh stamp instead of accumulating (`transcript_20260904_101500_20260904_101512.txt`). File mode doesn't need this — its base name is always the fixed `{input_stem}_transcript`, never itself previously stamped.

**Stamp the field's actual value, not just the placeholder default (live mode).** A user who clicks "Browse…" and picks an exact filename still gets that value re-stamped before the session starts, and sees the stamped result written back into the field. This is a deliberate override of an explicit user choice — accepted because the alternative (respecting a browsed path verbatim) reopens exactly the overwrite risk for anyone who browses once, then clicks Start twice.

**File mode's stamp only applies to the auto-derived name.** An explicit `--output` (a real CLI use case, just not one the GUI exercises today) still writes to exactly the path given, untouched — this change only closes the gap in the branch the GUI actually uses.

## Risks / Trade-offs

- [Two runs starting within the same wall-clock second still collide] → Accepted; unreachable by a human clicking a button, only by scripted/automated starts. Upgrade path if that ever matters: sub-second resolution or a monotonic counter suffix.
- [Live mode silently rewrites a user's explicitly browsed filename] → Accepted per the Decisions section above; the field is updated visibly before the session starts, so the user sees what's actually being written — it isn't changed after the fact.

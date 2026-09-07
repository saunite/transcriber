## Context

See proposal.md - Why, and the source map traced during exploration: four independent print sites (`start_teams_transcription.bat`, `transcriber.py`'s generic banner, `transcriber.py`'s live-mode banner + device prints, `wasapi_capture.py`) each announce "starting"/"stopping" separately, with no shared sense of what a user actually needs to see by default.

## Goals / Non-Goals

**Goals:**
- A user watching a live/Teams session sees about 3 lines before the first transcript line, and 1 line on stop, by default.
- Full diagnostic detail (device names, banners, dual shutdown announcements) stays available via one flag, not deleted.
- The command printed by `start_teams_transcription.bat` can never drift from what's actually executed.

**Non-Goals:**
- File-mode's `Transcription Summary` block — a separate, smaller problem, not in scope here.
- Any change to how the GUI parses/displays sidecar output. `src-tauri/src/sidecar.rs`'s `TRANSCRIPT_LINE_RE` already only picks out `[ts] [tag] text`-shaped lines and routes everything else (banners included) to the debug log panel; that regex, and what counts as a "recognized transcript line," is unchanged by this proposal.
- Adding `--verbose` to file-mode transcription — its output is already comparatively compact; can be picked up separately if wanted.

## Decisions

**One `--verbose` flag, not a `--quiet`/default-verbose split.** Compact becomes the new default; `--verbose` is the opt-in for the old detail. This matches the direction actually wanted (compact by default) rather than requiring every existing launcher habit to learn a new default-suppression flag.

**`--verbose` is additive, not a separately-worded mode.** Verbose output is the new compact lines plus the existing detail lines interleaved in — not a third, differently-worded format to maintain. This keeps the change to "gate existing prints behind a condition" rather than "invent and maintain two full parallel output vocabularies."

**`wasapi_capture.py`'s own prints are also gated, from the same flag, passed through from `transcriber.py`.** This project already threads capture-module config through from `transcriber.py`'s CLI args to the WASAPI/Core Audio capture classes — `verbose` is one more such pass-through, no new plumbing shape.

**`start_teams_transcription.bat` prints the actual command, not a paraphrase.** Built as one variable (`set "CMD=..."`), echoed, then executed from that same variable. A paraphrased banner (like today's) can silently drift out of sync with the real invocation as flags get added over time; echoing the literal command line structurally can't.

**The `.bat`'s banner is removed unconditionally, not gated behind anything.** It has no access to `transcriber.py`'s `--verbose` flag — it runs before `transcriber.py` is invoked at all. The literal-command-line replacement is the compact default *and* the only version there is, from the launcher's side. A user who wants `transcriber.py`'s own verbose detail still gets it by passing `--verbose` through the launcher's existing passthrough args, e.g. `start_teams_transcription.bat sprint-review --verbose`.

## Risks / Trade-offs

- [The `Terminate batch job (Y/N)?` prompt `cmd.exe` shows on Ctrl+C during a `.bat` is untouched] → Accepted; that's `cmd.exe` itself intercepting the interrupt, not this app's output — out of reach from Python or the `.bat`'s own echo statements.
- [A user relying on muscle memory, or a saved script that greps the old verbose-by-default output for a specific line] → Accepted as a real but small breakage; `--verbose` restores the exact old text if needed.

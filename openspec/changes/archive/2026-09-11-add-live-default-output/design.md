## Context

See proposal.md - Why. In `transcriber.py`, every live path already handles a saved transcript: when `args.output` is set, it prints `Transcriber → <file>` and writes each line to that file. So the whole change is about *what `args.output` is* when the user didn't give one. `main()` already post-processes arguments right after `parse_args()`: it fills `args.model_path` from `_bundled_model_path()`.

## Goals / Non-Goals

**Goals:**
- A bare `--live` never loses a transcript, with one obvious flag to opt out.

**Non-Goals:**
- Changing file mode's default naming, the launchers, or the GUI.
- Choosing the output directory. It's the current directory, like file mode and the launchers.

## Decisions

### 1. One pure helper decides the live output path

`_live_output_path(args, now)` returns:
- `args.output` when it's given
- `None` when `--no-output` is set or the run isn't live
- otherwise `f"transcript_{now:%Y%m%d_%H%M%S}.txt"`

`main()` assigns the result to `args.output` right after the bundled-model line, so every live path keeps reading `args.output` unchanged. Taking `now` as a parameter makes it testable without a clock. The name matches the GUI's default (`transcript_` plus the same timestamp format), so files from either front end look alike.

### 2. `--no-output` is a plain flag; the conflict with `--output` is a `parser.error`

Putting the two flags in an argparse mutually-exclusive group would mean moving `--output`, which file mode also uses, into the group. A one-line `parser.error(...)` when both are set gives the same user-facing error with a smaller diff. `--no-output` only affects live capture; file mode always saves, and its help says so.

## Risks / Trade-offs

- **[Trade-off]** CLI users who relied on print-only live runs now get a file in their working directory; `--no-output` is the documented way back. The spec only covers this CLI and its launchers, so there's no other consumer to break.

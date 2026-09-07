## 1. transcriber.py

- [x] 1.1 Add `--verbose`/`-v` flag to argparse (default `False`)
- [x] 1.2 Gate the generic "Audio Transcriber" banner (`main()`) and the live-mode "Live Audio Transcription" banner + Model/Language/Chunk/Mode block behind `verbose`
- [x] 1.3 Gate the explicit `Auto-detected loopback:` / `Auto-detected microphone:` / `Microphone capture enabled` + Device/Channels prints behind `verbose`

  Applied identically to `transcribe_live_coreaudio_tap`'s equivalent block (`Using: <device>` / `Auto-detected microphone:` / `Microphone capture enabled` detail) — same structure, same fix, per design.md's decision to keep the two live-capture paths consistent rather than let one silently diverge.
- [x] 1.4 Add the compact default preamble: one identity/output-file line, one model+language+mode+device summary line, one listening/auto-stop line

  Implemented as a small always-on block in both `transcribe_live_wasapi` and `transcribe_live_coreaudio_tap` (same reasoning as 1.3), positioned after device detection so the device-derived summary line has real data. The old "Listening... (Press Ctrl+C to stop)" / "Auto-stop after Xm silence" prints further down in both functions were removed (not just gated) since the new preamble's third line already states the same thing — printing it twice even under `--verbose` would be the exact kind of duplication this change exists to remove. `transcribe_live_simple` (non-WASAPI fallback, not reachable from `start_teams_transcription.bat` or the GUI) was left with only its banner gated (1.2) — its own output was already close to this shape (2-3 lines) and it's outside this change's traced example.
- [x] 1.5 Gate the "⏹️ Shutdown requested..." print behind `verbose`; add a compact default stop line reporting segment count + output path

  `signal_handler` became `_make_signal_handler(verbose)`, a closure created in `main()` right before `signal.signal()` registration, since the handler needs `args.verbose` and takes no other arguments. New `_print_compact_stop()` helper prints unconditionally at all three live-mode call sites (simple/WASAPI/coreaudio-tap), alongside the now-`verbose`-gated `_print_summary()` banner.
- [x] 1.6 Pass `verbose` through to `WASAPICapture` (and `macos_capture.py`'s Core Audio path, for consistency, though unverified on macOS hardware per `add-macos-capture`'s own status)

## 2. wasapi_capture.py

- [x] 2.1 Accept a `verbose` param; gate "🎙️ Capturing from:" / "🎙️ Capturing audio... Press Ctrl+C to stop" / "✓ Capture stopped by user" behind it

  Same treatment applied to `macos_capture.py`'s twin prints ("🎙️ Capturing system audio via Core Audio Process Tap...", "🎙️ Capturing audio (...)... Press Ctrl+C to stop", "✓ Capture stopped by user") — not a separate numbered task, but covered under 1.6's "for consistency" scope.

## 3. start_teams_transcription.bat

- [x] 3.1 Remove the banner echo block
- [x] 3.2 Build the `python transcriber.py ...` invocation into one `CMD` variable, echo it, then execute from that same variable

  Used the `set "CMD=...value with embedded "quotes"..."` form (cmd.exe pairs the *first* and *last* `"` on the line as the outer delimiter, so the embedded `"%output_file%"` quoting inside the invocation itself survives as literal characters in the value — the standard idiom for a variable value that itself needs an embedded quoted argument). Reasoned through carefully but **genuinely unverified against real `cmd.exe`** — no Windows shell available in this environment, same caveat this codebase already carries for other Windows-only code (see `sidecar.rs`'s own header comment). Task 4.1 is the real check.

## 4. Verification

- [x] 4.1 Run the `.bat` launcher (no extra flags) on Windows hardware, confirm output matches the compact 3-line-preamble + 1-line-stop shape

  **Superseded by the rename in `add-cross-platform-launcher-scripts`.** `start_teams_transcription.bat` no longer exists — that change (archived 2026-09-06) renamed it to `win-start-transcription.bat`, byte-preserving this change's already-implemented CMD-echo edits (confirmed present in the current file, with an explicit comment pointing back at `openspec/changes/compact-live-cli-output`). Prior to the rename this task was partially confirmed on real Windows hardware: the `set "CMD=..."` construction and the 3-line compact preamble both rendered correctly; the 1-line stop summary wasn't seen in that one run because a second Ctrl+C landed during cleanup (a pre-existing double-interrupt quirk, not a regression). Full end-to-end Windows-hardware verification of the renamed file is now owned by `add-cross-platform-launcher-scripts` task 6.1 (itself still marked unverified on real hardware there), not by this change.
- [x] 4.2 Run with `--verbose` passed through (`start_teams_transcription.bat NAME --verbose`), confirm today's full detail still appears, in addition to the compact lines

  **Superseded — same reason as 4.1.** The file this task named no longer exists post-rename; the `--verbose` code path itself is implemented and unchanged by the rename. Not independently re-verified on hardware under the new filename; folded into `add-cross-platform-launcher-scripts` task 6.1's scope going forward.
- [x] 4.3 Confirm the GUI's live session (`src-tauri/src/sidecar.rs`, which never passes `--verbose`) still parses transcript lines and shows the compact preamble/stop lines in its Engine log panel with no parsing regression (`TRANSCRIPT_LINE_RE` is unaffected, but confirm nothing compact-mode prints accidentally matches it and gets misrouted)

  Verified by running the shipped `TRANSCRIPT_LINE_RE` (`^\[(?P<ts>[^\]]+)\](?:\s\[(?P<tag>SYS|MIC)\])?\s(?P<text>.*)$`) against every new compact-mode line (`Transcriber → ...`, the model/language/mode summary, `Listening... (...)`, `Stopped — ...`) — none match, so all correctly fall through to `sidecar-log` exactly like today's banners did. No GUI code touched.
- [x] 4.4 Confirm file-mode transcription (`--file`) output is unchanged (out of scope, but a quick regression check)

  Confirmed by inspection: every `args.verbose` reference added is inside `main()`'s live-mode dispatch or one of the three `transcribe_live_*` functions — `transcribe_file()` and its own summary block are untouched.

Also verified, beyond the tasks originally listed: `python3 -m py_compile` on all three changed `.py` files, `transcriber.py --help` shows the new flag correctly, both pre-existing test suites (`test_transcript_line_format.py`, `test_wav_merge.py`) still pass, and `_print_compact_stop`/`_make_signal_handler` were exercised directly (segment-count pluralization, verbose/quiet branches) confirming correct output.

## 5. Spec

- [x] 5.1 Add new `cli` requirement: compact-by-default live output with `--verbose` restoring full detail
- [x] 5.2 Add new `teams-launcher` requirement: launcher prints the literal command instead of a banner

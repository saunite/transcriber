## 1. Windows: rename only

- [x] 1.1 `git mv start_teams_transcription.bat win-start-transcription.bat` — verify the file's content is byte-identical after the rename (no behavior change) and `git status` shows a rename, not a delete+add

  Done: `md5sum` matches before/after (`f8276a2ff844523fdb4ffa56983ac764`), `git status --short` shows `R  start_teams_transcription.bat -> win-start-transcription.bat`.

## 2. Linux launcher

- [x] 2.1 Create `linux-start-transcription.sh`: port the batch script's argument convention (leading non-`-` argument is the name-prefix, default `meeting`; remaining args pass through) into bash, reusing `linux_start_transcription.sh`'s existing venv-detection idiom (prefer `.venv/bin/python`, fall back to `python3`) — verify `./linux-start-transcription.sh --help` (no name-prefix) and `./linux-start-transcription.sh sprint-review --silence-timeout 0` both parse correctly (echo the parsed name-prefix and remaining args to check)

  Done and verified: `--help` (starts with `-`) correctly leaves `NAME_PREFIX` at default `meeting` and passes `--help` straight through to `transcriber.py`; `sprint-review --silence-timeout 0 --list-devices` correctly captures `sprint-review` as the name-prefix and passes the rest through, confirmed via the echoed command line in both cases.

- [x] 2.2 Build the `transcriber.py` invocation as a bash array (`CMD=(...)`), not a string, with `--live --include-mic --model base --output "$output_file" --chunk-duration 10 --actual-time` plus the passed-through args (no `--wasapi`/`--coreaudio-tap` — Linux's dual-source path is the default `--live` path once `--include-mic` is set) — echo the array (`printf '%q ' "${CMD[@]}"` or equivalent) then execute it (`"${CMD[@]}"`) so the printed line can't drift from what runs — verify by running with `--silence-timeout 0` and confirming the echoed line matches the actual `ps`/process args

  Done and verified: ran the script with `--silence-timeout 0`, captured the live `transcriber.py` process via `ps`, and its args are byte-for-byte identical to the line the script echoed before executing.

- [x] 2.3 `chmod +x linux-start-transcription.sh` — verify `ls -l` shows the executable bit and `./linux-start-transcription.sh` runs without `bash` being invoked explicitly

  Done: `ls -l` shows `-rwxr-xr-x`; ran via `./linux-start-transcription.sh ...` (no explicit `bash` prefix) successfully.

  (Renumbered from 2.4 — the disclosure task originally numbered 2.3 was dropped: Linux dual-capture landed for real via `add-linux-dual-source-live-capture`/`fix-linux-loopback-detection` since this change was proposed, so the script passes `--include-mic` like the other two platforms instead of disclosing a limitation that's no longer true. See proposal.md/design.md/specs, updated accordingly before implementation.)

## 3. macOS launcher

- [x] 3.1 Create `mac-start-transcription.sh`: same argument convention and `CMD`-array pattern as the Linux script (task 2.1/2.2), but with `--coreaudio-tap --include-mic` instead of plain `--live`, and no PulseAudio-equivalent device-scanning preamble (Core Audio Tap needs none) — verify the script's structure by inspection against `linux-start-transcription.sh`, since no macOS hardware exists in this environment to run it (same caveat this codebase already carries for other macOS-only code)

  Done. Verified by inspection/diff against `linux-start-transcription.sh`: identical structure (arg parsing, venv detection, `CMD`-array build/echo/execute pattern), differing only in the intended ways — `--coreaudio-tap --include-mic` instead of plain `--include-mic`, and comments noting no device-scanning preamble is needed. `bash -n` syntax-check passes. Genuinely unverified end-to-end — no macOS hardware in this environment, same caveat as the rest of this codebase's macOS-only code.

- [x] 3.2 `chmod +x mac-start-transcription.sh`

  Done: `ls -l` shows `-rwxr-xr-x`.

## 4. Spec coordination

- [x] 4.1 Update the filename reference in the still-open `compact-live-cli-output` change's own pending delta spec (`openspec/changes/compact-live-cli-output/specs/teams-launcher/spec.md`) from `start_teams_transcription.bat` to `win-start-transcription.bat`, so it stays correct whenever that change eventually archives and syncs — verify by re-reading the file after the edit

  Done: replaced both occurrences (the requirement text and the scenario's example command). Re-read the file — both now say `win-start-transcription.bat`, nothing else in the file changed.

## 5. Documentation

- [x] 5.1 Update `README.md` and any other docs referencing `start_teams_transcription.bat` by its old name, and add a mention of the new Linux/macOS launchers alongside it — verify with `grep -rn "start_teams_transcription.bat"` returning no remaining hits anywhere in the repo (docs or code)

  Done, with one deliberate deviation from the literal "zero hits anywhere" bar: updated every **live/current-facing** reference — `README.md` (both the Quick Start section and the Launchers section, plus adding the new `linux-start-transcription.sh`/`mac-start-transcription.sh` entries), `win-start-transcription.bat`'s own internal Usage/Example comments (previously still said the old filename after the rename), and two source comments referencing it by name (`src-tauri/src/sidecar.rs`, `src/main.js`). Left references untouched in: archived changes (`openspec/changes/archive/**`, frozen historical record) and the still-open `compact-live-cli-output`/this-change's own proposal.md/design.md/tasks.md narrative text describing already-completed work or the rename itself under the old name — matching this repo's established convention (see e.g. `05-remove-installer-packaging-windows`'s own precedent) of never rewriting historical prose, only forward-looking specs (already handled in task 4.1) and live docs/code.

  Also fixed two bugs found while touching this section, both pre-existing and unrelated to the rename itself: (1) `README.md`'s Linux setup section referenced a nonexistent `./start_transcription.sh` (should be the actual pre-existing `linux_start_transcription.sh`) in two places; (2) added the missing macOS/Linux launcher examples to the "Launchers" code block, which only listed Windows scripts.

## 6. Verification

- [x] 6.1 Confirm `win-start-transcription.bat` behavior is unaffected by the rename — this needs Windows hardware to actually run (same class of blocker as `compact-live-cli-output`'s own tasks 4.1/4.2); at minimum, confirm no other file in the repo (docs, other scripts) still references the old filename and would silently break

  Content confirmed byte-identical by the rename itself (task 1.1). Confirmed no functional/build-time dependency on the old filename anywhere: `grep` across `.github/`, `src-tauri/`, and root-level `.json`/`.toml`/`.yml`/`.yaml` files returns zero hits — nothing packages, bundles, or invokes the launcher by its old name. **Not verified**: actually double-clicking/running it on Windows — genuinely needs Windows hardware, unavailable in this environment, same caveat as the rest of this codebase's Windows-only verification gaps.
- [x] 6.2 Run `linux-start-transcription.sh` on this Linux machine end-to-end (a short live session, Ctrl+C to stop) and confirm it behaves like `win-start-transcription.bat` in shape (same defaults, same compact output shape, correct timestamped output file produced) including passing `--include-mic`; real mic content still needs a human (same limitation `add-linux-dual-source-live-capture` task 3.1 already flagged)

  Verified end-to-end: ran the script for a few seconds with `--silence-timeout 0`, then Ctrl+C. Echoed line: `.../.venv/bin/python transcriber.py --live --include-mic --model base --output e2etest_20260906_014638.txt --chunk-duration 10 --actual-time --silence-timeout 0`. Compact preamble printed correctly with the real dual-source device names: `Transcriber → e2etest_....txt` / `base model (cpu/int8), auto-detect language, System audio (alsa_output.pci-....monitor) + mic (default)` / `Listening... (Ctrl+C to stop)`. Output file produced with the correct timestamped name and header. No transcribed segment in this particular short run — expected, not a bug: `base` model + the script's fixed `--chunk-duration 10` means the first chunk boundary hadn't been reached yet in the few seconds before Ctrl+C; segment-producing behavior with real played audio was already proven extensively against this exact dual-source code path in `fix-linux-loopback-detection`'s own verification. Real human-spoken mic content is still the one thing that needs a person, unchanged from `add-linux-dual-source-live-capture` task 3.1.

## 1. Stop bundling the build host's libasound

- [ ] 1.1 Give the Linux freeze a spec-file (or post-filtered analysis) route in `build_sidecar.py` that drops the top-level `libasound.so*` entries from PyInstaller's `a.binaries`, keeping every existing flag's effect intact — `--onefile`, the `transcriber-sidecar` name, `dist/<system>`, `build/<system>`, the `faster_whisper/assets` data, and the Windows/macOS `--icon` (design.md Decision 1). Verify `python build_sidecar.py` still exits 0 on Linux and produces `dist/linux/transcriber-sidecar`, and that Windows/macOS invocations are unchanged by inspection of the assembled argument list.
- [ ] 1.2 Confirm PyAV's private copy survives: the rebuilt binary must still contain `av.libs/libasound-<hash>.so.2.0.0` while the top-level `libasound.so.2` is gone (design.md Decision 1 — removing PyAV's copy would risk file transcription, which never broke). Verify by listing the frozen bundle's contents, or with `LD_DEBUG=libs` showing the `av.libs` copy still loading and the top-level one now resolving to a host path such as `/usr/lib64/libasound.so.2`.
- [ ] 1.3 Verify the rebuilt sidecar on this Fedora machine: `--list-devices-json` reports input devices including `pipewire`/`default` (against the CI binary's 0 inputs from 4 HDMI-only devices), and `--live --include-mic --no-output --model-path src-tauri/resources/model` reaches `Listening...` and transcribes a `[MIC]` segment. This is the same check that `LD_PRELOAD=/usr/lib64/libasound.so.2` already passed against the unmodified CI binary, now without the preload.

## 2. Microphone resolution degrades instead of exiting

- [ ] 2.1 Replace the three duplicated auto-detect blocks in `transcriber.py` (`:754` Linux dual-capture, `:1008` WASAPI, `:1246` macOS tap) with one shared helper they all call (design.md Decision 2). Verify by grepping that `Could not auto-detect microphone` appears in exactly one place and that all three capture paths route through the helper.
- [ ] 2.2 Implement the fallback the spec deltas require: with no resolvable default input but other devices reporting input channels, select the first such device and name it in the output; with no input device at all, report that, name `--list-devices` and `--mic-device`, and exit non-zero. An explicitly specified invalid device SHALL keep aborting as today (`audio-capture`'s "Invalid microphone device" scenario is unchanged). Verify with a test that fakes the device layer for all three cases — default resolvable, default missing with inputs present, no inputs at all.
- [ ] 2.3 Add the runnable check as a plain `test_*.py` in the repo's existing style (`assert`-based, no framework), covering 2.2's three cases plus the unchanged explicit-bad-device abort. Verify it passes with `.venv/bin/python test_<name>.py` and fails if the fallback is removed.

## 3. Package dependencies

- [ ] 3.1 Add the ALSA runtime soname to `src-tauri/tauri.conf.json`'s `bundle.linux.rpm.depends`, beside the existing `libwebkit2gtk-4.1.so.0()(64bit)` and `libgtk-3.so.0()(64bit)` (design.md Decision 3). Verify the JSON parses, `cargo check` in `src-tauri/` reports no config error, and a built `.rpm`'s `rpm -qpR` lists all three.
- [ ] 3.2 Confirm the `.deb`'s generated dependencies include the ALSA library (its dependencies are derived, not hand-listed). Verify with `dpkg-deb -f <deb> Depends` on a built package; if it is absent, add it explicitly rather than assuming the derivation covers it.

## 4. CI verification

- [ ] 4.1 On the next tagged run, confirm the Linux job still builds and that the published `.rpm`, `.deb` and AppImage each contain no top-level bundled `libasound.so.2`. Verify by listing the packaged sidecar's bundle contents from the downloaded artifacts.
- [ ] 4.2 Confirm the five install checks still pass, in particular `fedora:latest` and both openSUSE images, which must now resolve the new ALSA dependency from their own repositories. A missing or misnamed soname would surface as a dnf/zypper dependency error rather than a runtime failure.

## 5. Real-hardware verification

- [ ] 5.1 Install the CI-built `.rpm` on the Fedora machine and confirm the GUI's microphone dropdown now lists real input devices rather than only "System default (recommended)" — the visible symptom the user reported.
- [ ] 5.2 Start a live session from that installed `.rpm` with the default mic selection and confirm it captures: no `Could not auto-detect microphone`, no `engine exited unexpectedly`, and both `[SYS]` and `[MIC]` segments appear. This is the exact flow that failed at 07:30 and 07:40.
- [ ] 5.3 Confirm file transcription still works from the same installed package, proving the changed bundle did not disturb PyAV's decoding (design.md Decision 1's reason for keeping `av.libs`).
- [ ] 5.4 Check the AppImage from the same run for the **unexplained asymmetry** recorded in design.md Risks: its earlier build auto-detected `hw:0,0` and transcribed while every local run of that binary saw zero inputs. Record what the fixed AppImage now reports, so the intermittency question is answered with data rather than left open.
- [ ] 5.5 Verify the `.deb` does not regress on Debian or Ubuntu, where build-host and run-host ALSA layouts coincide and the bug was therefore invisible (design.md Decision 4). A live session there must behave exactly as before this change.
- [ ] 5.6 Extract the Linux CLI archive and confirm `./transcriber --live --include-mic` captures on Fedora, since the CLI ships the same frozen sidecar and had the same defect.

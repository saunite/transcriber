## 1. Stop bundling the build host's libasound

- [x] 1.1 Give the Linux freeze a spec-file (or post-filtered analysis) route in `build_sidecar.py` that drops the top-level `libasound.so*` entries from PyInstaller's `a.binaries`, keeping every existing flag's effect intact — `--onefile`, the `transcriber-sidecar` name, `dist/<system>`, `build/<system>`, the `faster_whisper/assets` data, and the Windows/macOS `--icon` (design.md Decision 1). Verify `python build_sidecar.py` still exits 0 on Linux and produces `dist/linux/transcriber-sidecar`, and that Windows/macOS invocations are unchanged by inspection of the assembled argument list.
- [x] 1.2 Confirm PyAV's private copy survives: the rebuilt binary must still contain `av.libs/libasound-<hash>.so.2.0.0` while the top-level `libasound.so.2` is gone (design.md Decision 1 — removing PyAV's copy would risk file transcription, which never broke). Verify by listing the frozen bundle's contents, or with `LD_DEBUG=libs` showing the `av.libs` copy still loading and the top-level one now resolving to a host path such as `/usr/lib64/libasound.so.2`.
- [x] 1.3 Verify the rebuilt sidecar on this Fedora machine: `--list-devices-json` reports input devices including `pipewire`/`default` (against the CI binary's 0 inputs from 4 HDMI-only devices), and `--live --include-mic --no-output --model-path src-tauri/resources/model` reaches `Listening...` and transcribes a `[MIC]` segment. This is the same check that `LD_PRELOAD=/usr/lib64/libasound.so.2` already passed against the unmodified CI binary, now without the preload.


  **Implemented and verified locally 2026-09-12 (Fedora 44, PyInstaller 6.22.2).**

  - **1.1** The build now runs from a committed `transcriber-sidecar.spec`; `build_sidecar.py` passes only `--distpath`, `--workpath`, `--noconfirm` and the spec path. Everything the old flags did moved into the spec, because **a spec-based build ignores `--onefile`, `--name`, `--add-data` and `--icon`** — leaving them on the command line would have silently stopped applying them. `python build_sidecar.py` exits **0** and produces `dist/linux/transcriber-sidecar` (159,053,960 bytes). `SPECPATH` and `TOC` are both injected into the spec namespace by PyInstaller 6.22.2 (`build_main.py:1189`/`:1193`), but the filter assigns a **plain list** rather than `TOC(...)`, since that source line marks the `TOC` class deprecated. Dead code removed in passing: `_faster_whisper_assets_dir()` and its `importlib.util` import lost their only caller, and the docstring's `--add-data` explanation was corrected.
  - **1.2** The build's `EXE-00.toc` contains **4** `libasound` lines and every one is PyAV's `av.libs/libasound-c7818c60.so.2.0.0`; the top-level `libasound.so.2` is gone. PyAV's copy still loads at runtime, so file transcription's decoder is untouched.
  - **1.3** With **no `LD_PRELOAD`**, the rebuilt sidecar reports **18 devices and 9 inputs** — `pipewire`, `default`, `sysdefault`, `samplerate`, `upmix`, `vdownmix`, `Built-in Audio Analog Stereo`, and `HDA Intel PCH: ALC257 Analog (hw:0,0)` — against the CI binary's **4 devices, 0 inputs**. Live capture works: it reached `Listening...`, auto-detected `mic (default)` plus the PipeWire monitor, and transcribed `[MIC]` segments.

  **The mechanism is confirmed by the loader, not inferred from file size.** `LD_DEBUG=libs` on the rebuilt binary shows `find library=libasound.so.2 [0]; searching` → `trying file=/lib64/libasound.so.2` → **`calling init: /lib64/libasound.so.2`**, and then all five host plugin modules loading from `/lib64/alsa-lib/` (`libasound_module_pcm_pipewire.so`, `_upmix`, `_usb_stream`, `_vdownmix`, `rate_samplerate`) — exactly what the CI binary never loaded.

  **One line in that trace looked like a failure and is not.** The same search also prints `trying file=/tmp/_MEI…/libasound.so.2`. That is a *later* probe in the one search whose winner was `/lib64/libasound.so.2` (the `calling init:` line names it), and the `_MEI` directory no longer exists after the run. Checked explicitly rather than assumed, because the 522 KB size drop alone would have been the same kind of inference that produced earlier wrong figures in this project.

## 2. Microphone resolution degrades instead of exiting

- [x] 2.1 Replace the three duplicated auto-detect blocks in `transcriber.py` (`:754` Linux dual-capture, `:1008` WASAPI, `:1246` macOS tap) with one shared helper they all call (design.md Decision 2). Verify by grepping that `Could not auto-detect microphone` appears in exactly one place and that all three capture paths route through the helper.
- [x] 2.2 Implement the fallback the spec deltas require: with no resolvable default input but other devices reporting input channels, select the first such device and name it in the output; with no input device at all, report that, name `--list-devices` and `--mic-device`, and exit non-zero. An explicitly specified invalid device SHALL keep aborting as today (`audio-capture`'s "Invalid microphone device" scenario is unchanged). Verify with a test that fakes the device layer for all three cases — default resolvable, default missing with inputs present, no inputs at all.
- [x] 2.3 Add the runnable check as a plain `test_*.py` in the repo's existing style (`assert`-based, no framework), covering 2.2's three cases plus the unchanged explicit-bad-device abort. Verify it passes with `.venv/bin/python test_<name>.py` and fails if the fallback is removed.


  **Implemented and verified locally 2026-09-12.**

  - **2.1** The three duplicated blocks are gone, replaced by one `_resolve_mic_device(args)` helper (`transcriber.py:477`, beside the other `_`-helpers) called from all three capture paths — `:784` Linux dual-capture, `:1029` WASAPI, `:1259` macOS tap. `grep -c "Could not auto-detect microphone"` is now **0** (the helper's own wording replaced it) and `grep -c '^\s\+except:\s*$'` is **0**: the WASAPI block's bare `except:` disappeared along with it, which was swallowing `KeyboardInterrupt` and `SystemExit` too.
  - **2.2** The helper passes an explicit `--mic-device` straight through (so `audio-capture`'s "Invalid microphone device" abort is untouched), auto-detects via `query_devices(kind='input')`, and on failure scans for the first device with `max_input_channels > 0`, naming it (`⚠️  No default microphone; using <name>`). With no input device at all it prints `❌ No microphone found.` plus the `--list-devices`/`--mic-device` guidance and returns `None`, which each caller turns into its existing non-zero exit.
  - **2.3** `test_mic_fallback.py` covers all four cases by injecting a fake `sounddevice` into `sys.modules`. **The mutation check the task asked for was actually run**: neutering the fallback scan makes case 2 fail with `(None, '❌ No microphone found. …')`, and the file was restored from a backup and passes again. So the test has teeth rather than passing vacuously.

  **The test earned its place immediately by catching a real defect in my first version of the helper.** `sounddevice` is imported *function-locally* in this file (`:584`, `:731`, `:993`, `:1238`), never at module scope, and my helper referenced a bare `sd` — which `py_compile` accepts happily and which would have raised `NameError` on the first live session, replacing one crash with another. Fixed by giving the helper its own deferred `import sounddevice as sd`, matching every other caller and preserving the reason for the deferral: importing `sounddevice` initialises PortAudio, and a `--file` run should not pay that cost.

## 3. Package dependencies

- [x] 3.1 Add the ALSA runtime soname to `src-tauri/tauri.conf.json`'s `bundle.linux.rpm.depends`, beside the existing `libwebkit2gtk-4.1.so.0()(64bit)` and `libgtk-3.so.0()(64bit)` (design.md Decision 3). Verify the JSON parses, `cargo check` in `src-tauri/` reports no config error, and a built `.rpm`'s `rpm -qpR` lists all three.
- [x] 3.2 Confirm the `.deb`'s generated dependencies include the ALSA library (its dependencies are derived, not hand-listed). Verify with `dpkg-deb -f <deb> Depends` on a built package; if it is absent, add it explicitly rather than assuming the derivation covers it.


  **3.1 done locally 2026-09-12.** `bundle.linux.rpm.depends` now lists `libasound.so.2()(64bit)` beside `libwebkit2gtk-4.1.so.0()(64bit)` and `libgtk-3.so.0()(64bit)`. The soname was taken from the local rpm database rather than guessed — `rpm -q --provides alsa-lib` reports exactly `libasound.so.2()(64bit)` (from `alsa-lib-1.2.16.1-1.fc44`), and `/lib64/libasound.so.2` is owned by that package. A misnamed soname would fail at install time on Fedora/openSUSE rather than at build time, which is why it was checked against the database. The JSON parses and `cargo check` in `src-tauri/` reports no config error.


  **3.2 done 2026-09-12, and the derivation did NOT cover it — as suspected.** `dpkg-deb -f transcriber_0.1.0_amd64.deb Depends` on the published package listed only `libwebkit2gtk-4.1-0, libgtk-3-0`: no ALSA. Tauri derives deb dependencies from the GUI binary, which does not link ALSA — the need lives inside the frozen sidecar, where PortAudio dlopens it, and that is invisible to the derivation. So `bundle.linux.deb.depends: ["libasound2"]` was added explicitly (Debian/Ubuntu's package name, against the rpm's `libasound.so.2()(64bit)` soname form). JSON parses and `cargo check` accepts the key. The published `.deb` carrying the dependency is only provable on the next tagged run.

## 4. CI verification

- [x] 4.1 On the next tagged run, confirm the Linux job still builds and that the published `.rpm`, `.deb` and AppImage each contain no top-level bundled `libasound.so.2`. Verify by listing the packaged sidecar's bundle contents from the downloaded artifacts.
- [x] 4.2 Confirm the five install checks still pass, in particular `fedora:latest` and both openSUSE images, which must now resolve the new ALSA dependency from their own repositories. A missing or misnamed soname would surface as a dnf/zypper dependency error rather than a runtime failure.


  **Verified on tagged run 34699748992 (v0.1.0 re-run, 2026-09-12) — all three jobs succeeded, 12m24s.**

  - **4.1** No artifact bundles a top-level `libasound.so.2` any more. Each packaged sidecar was extracted and run on this Fedora machine, and all three now initialise the **host** library: `calling init: /lib64/libasound.so.2`, with PyAV's `av.libs/libasound-c7818c60.so.2.0.0` still initialising beside it exactly as Decision 1 intended.

    | Artifact | sidecar bytes | devices / inputs |
    |---|---|---|
    | `.rpm` | 175,481,184 | 16 / **7** |
    | `.deb` | 175,481,184 | 16 / **7** |
    | AppImage | 175,485,280 | 16 / **7** |

    Against the previous CI build's **4 devices / 0 inputs**, on the same machine. The AppImage's copy is 4,096 bytes larger because linuxdeploy stamps `rpath: $ORIGIN/../lib` on it; run without that directory present it exits 255 with empty stdout/stderr (the bootloader failing before Python starts), so it must be tested with its `usr/lib` extracted — two earlier "empty result" runs here were that, plus a full tmpfs, not a defect in the build.
  - **4.2** All five install checks passed — `debian:stable`, `ubuntu:24.04`, `fedora:latest`, `opensuse/leap:latest`, `opensuse/tumbleweed` — so the new `libasound.so.2()(64bit)` rpm dependency resolves on every target. The lone `::error` string in the log is again the workflow echoing its own un-expanded `echo "::error::install check failed on $img"` template. **Not verified:** I could not find lines showing `alsa-lib`/`libasound2` actually being *pulled in* during those transactions, so the dependency resolving is proven by the installs succeeding, not by observing the package being fetched.

  **Unrelated but confirmed in the same run:** rpm bundling stayed at **4.08 s** (14:42:00.75 → 14:42:04.83), and the AppImage still carries only `libwayland-cursor`/`libwayland-server`, so `fix-appimage-egl-crash`'s strip survived this build.

## 5. Real-hardware verification

- [ ] 5.1 Install the CI-built `.rpm` on the Fedora machine and confirm the GUI's microphone dropdown now lists real input devices rather than only "System default (recommended)" — the visible symptom the user reported.
- [ ] 5.2 Start a live session from that installed `.rpm` with the default mic selection and confirm it captures: no `Could not auto-detect microphone`, no `engine exited unexpectedly`, and both `[SYS]` and `[MIC]` segments appear. This is the exact flow that failed at 07:30 and 07:40.
- [ ] 5.3 Confirm file transcription still works from the same installed package, proving the changed bundle did not disturb PyAV's decoding (design.md Decision 1's reason for keeping `av.libs`).
- [ ] 5.4 Check the AppImage from the same run for the **unexplained asymmetry** recorded in design.md Risks: its earlier build auto-detected `hw:0,0` and transcribed while every local run of that binary saw zero inputs. Record what the fixed AppImage now reports, so the intermittency question is answered with data rather than left open.
- [ ] 5.5 Verify the `.deb` does not regress on Debian or Ubuntu, where build-host and run-host ALSA layouts coincide and the bug was therefore invisible (design.md Decision 4). A live session there must behave exactly as before this change.
- [ ] 5.6 Extract the Linux CLI archive and confirm `./transcriber --live --include-mic` captures on Fedora, since the CLI ships the same frozen sidecar and had the same defect.

## Why

Live transcription does not work in the released Linux packages. On Fedora 44 (Wayland/KDE, PipeWire) the installed `.rpm` loads its model, then prints `⚠️ Could not auto-detect microphone` and the GUI reports `Capture engine exited unexpectedly (code Some(1))`. The microphone dropdown offers nothing but "System default (recommended)", so there is no device for the user to pick instead. File transcription is unaffected.

The cause is measured, not inferred. PyInstaller bundles the **build host's** `libasound.so.2`, and a bundled `libasound` carries the ALSA plugin directory it was compiled with. CI freezes on `ubuntu-22.04`, whose `libasound` searches `/usr/lib/x86_64-linux-gnu/alsa-lib` — a path that does not exist on Fedora. `libasound_module_pcm_pipewire.so` is therefore never loaded, no `pipewire`/`default`/`pulse` PCM is defined, and PortAudio sees only bare ALSA hardware:

| Sidecar | Devices seen on this Fedora machine | Inputs |
|---|---|---|
| CI-built (Ubuntu 22.04 freeze) | 4 — all HDMI outputs (`hw:0,3`, `hw:0,7`, `hw:0,8`, `hdmi`) | **0** |
| Locally built (Fedora 44 freeze) | 9 — incl. `pipewire`, `default`, `Built-in Audio Analog Stereo` | 5 |

`LD_DEBUG=libs` confirms the mechanism: both load a bundled `/tmp/_MEI*/libasound.so.2`, but only the Fedora-frozen one goes on to load `/usr/lib64/alsa-lib/libasound_module_pcm_pipewire.so`. The CI binary loads no plugin modules at all. Identical results from the rpm's copy, the AppImage's copy, from inside the mounted AppImage, and with the test sandbox disabled.

With no default input, `sd.query_devices(kind='input')` raises and the mic auto-detect branch does `return 1` — an immediate exit instead of degrading. **This affects every CI-built Linux artifact**, including system-audio capture, since the monitor source is equally invisible.

## What Changes

- **The frozen sidecar stops shipping its build host's `libasound`**, so the host's copy — with the correct plugin directory for the running distribution — is used instead. Validated end to end: `LD_PRELOAD=/usr/lib64/libasound.so.2` on the **unmodified** CI binary makes it enumerate `pipewire`/`default` *and* capture, reaching "Listening…", selecting `mic (default)` plus the PipeWire monitor for system audio, and transcribing live `[MIC]` segments. Nothing else about the binary needs to change.
- **Microphone auto-detection degrades instead of aborting.** When no default input can be resolved, fall back to the first device that actually has input channels; when there is genuinely none, fail with guidance naming `--list-devices` and `--mic-device` rather than a bare exit. Fixed once in the shared path so all three call sites benefit — `transcriber.py:754` (Linux dual-capture), `:1008` (WASAPI) and `:1246` (macOS tap) each repeat the same `return 1`.
- **The `.deb` and `.rpm` declare their ALSA runtime dependency**, since the packages now rely on the host providing `libasound`.
- **Not changed**: the GUI plumbing, which is verified innocent. `main.js` sends `micDevice: null` for the "System default" entry, `sidecar.rs` then omits `--mic-device`, and argparse's `-1` default correctly routes into auto-detection. The bug is entirely below that.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities

- `audio-capture`: "Capture microphone audio" — its only failure scenario today is "Invalid microphone device… reports an error and aborts the run", which conflates an explicitly-specified bad device with *auto-detection* finding nothing. The delta separates them: a failed auto-detection falls back to an available input device, and only aborts when no input device exists at all.
- `cli`: "Select Linux dual-source live capture mode" — extends the existing degradation guarantee. That requirement already states that a microphone which cannot open at 16 kHz is opened at its own rate and resampled "rather than failing the session"; this adds the companion rule that a microphone which cannot be auto-detected falls back to an available input rather than failing the session.

Deliberately **not** modified: `cli`'s "Provide machine-readable device listing". It requires `--list-devices-json` to print what the audio layer reports, and it did exactly that — the empty dropdown was this bug's symptom, not a violation of that requirement.

## Impact

- **Changed**: `build_sidecar.py` (how PyInstaller is invoked — it currently passes CLI flags only, and PyInstaller has no flag to exclude a bundled *binary*), `transcriber.py` (the shared mic-resolution path), `src-tauri/tauri.conf.json` (`.rpm` depends), `.github/workflows/release.yml` if the build needs an extra package.
- **Effect**: live capture works in the released Linux packages on distributions whose ALSA layout differs from the build host's — which is every non-Debian distribution, i.e. two of the four this project install-tests.
- **Risk carried into design**: one observation remains **unexplained**. The user's AppImage run at 08:41 *did* auto-detect `HDA Intel PCH: ALC257 Analog (hw:0,0)` and transcribed live, while every run of that same binary here — including from inside the mounted AppImage — sees zero inputs. If the failure is intermittent (PortAudio's ALSA backend omits devices it cannot open, so a suspended or busy analog codec could appear and disappear), the degradation half is essential rather than cosmetic. It is not safe to assume the first half alone fixes this.
- **Disproven, do not retry**: `ALSA_PLUGIN_DIR=/usr/lib64/alsa-lib` changes nothing on the CI binary — Ubuntu 22.04's `libasound` ignores it. An environment-variable fix is not available.
- **Unchanged**: Windows and macOS capture paths (the degradation improves their failure message but alters no working behaviour), and file transcription, which never broke.

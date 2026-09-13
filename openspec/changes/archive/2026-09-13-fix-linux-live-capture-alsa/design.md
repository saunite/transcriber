## Context

See proposal.md - Why. The constraints that shape the approach:

- `build_sidecar.py` invokes PyInstaller through `subprocess.call` with CLI flags only: `--onefile`, `--name transcriber-sidecar`, `--distpath dist/<system>`, `--workpath build/<system>`, `--specpath build/<system>`, `--add-data <faster_whisper assets>`, and `--icon` on Windows/macOS. There is no `.spec` file in the repo — PyInstaller generates one into `build/<system>/` on every run.
- PyInstaller has **no CLI flag to exclude a bundled shared library**. `--exclude-module` filters Python modules, not binaries. Binary exclusion is only reachable by editing the analysis result, which means a spec file (or a hook).
- The bundled library set comes from PyInstaller's `sounddevice` hook, which pulls in PortAudio and its dependencies, `libasound.so.2` among them. PyAV separately carries its own `av.libs/libasound-<hash>.so.2.0.0`; `LD_DEBUG` shows **both** being loaded, and only the top-level one is what PortAudio resolves against.
- `.rpm` dependencies are declared in `src-tauri/tauri.conf.json` under `bundle.linux.rpm.depends` (currently the two WebKitGTK/GTK sonames). The `.deb` path derives its dependencies automatically today.

## Goals / Non-Goals

**Goals:**
- Live capture works in the released Linux artifacts on distributions whose ALSA layout differs from the build host's.
- A failed microphone auto-detection never ends a live session while a usable input device exists.

**Non-Goals:**
- Changing how system audio is captured. That path already shells out to `pactl`/`parec` and is unaffected by PortAudio's device view; it fails here only because the whole ALSA layer is crippled.
- Making the sidecar work on a host with no ALSA runtime at all. Relying on the host is the fix, not a regression to hedge against.
- Bundling a *newer* `libasound`, or bundling ALSA plugin modules. Both re-create the same class of bug one distribution further along.
- Fixing the Windows/macOS capture paths. They inherit the better failure message and nothing else.

## Decisions

### 1. Stop bundling `libasound.so.2`; let the host provide it

This is the measured fix: `LD_PRELOAD=/usr/lib64/libasound.so.2` on the **unmodified** CI binary restores both enumeration (`pipewire`, `default`) and capture (reached "Listening…", transcribed `[MIC]` segments). Using the host's copy is also correct by construction — the host's `libasound` is the one whose compile-time plugin directory matches the host's plugin files.

Implementation: give `build_sidecar.py` a committed `.spec` for the Linux build (or generate one and post-filter) that drops the top-level `libasound.so*` entries from `a.binaries`. Everything else about the invocation stays as it is.

**Only the top-level entry is dropped.** PyAV's `av.libs/libasound-<hash>.so.2.0.0` stays: it is PyAV's private dependency for media decoding, is loaded under its own path, and has nothing to do with PortAudio's device enumeration. Removing it would risk file transcription, which is not broken.

**Rejected: `ALSA_PLUGIN_DIR`.** Tested directly — `ALSA_PLUGIN_DIR=/usr/lib64/alsa-lib` leaves the CI binary at 0 inputs. Ubuntu 22.04's `libasound` ignores it. Recorded so this is not retried as an "obvious" cheap fix.

**Rejected: `LD_PRELOAD` at spawn time.** It works (it is how the fix was proven), but it would have to be repeated in `sidecar.rs`, in `linux-start-transcription.sh`, and by anyone running the CLI binary directly, with a hardcoded per-distribution library path. That is a workaround spread across three places rather than a fix in one.

**Rejected: a PyInstaller runtime hook.** A hook could rewrite the search path before `sounddevice` imports, but it has to guess the host's plugin directory (`/usr/lib64/alsa-lib` vs `/usr/lib/x86_64-linux-gnu/alsa-lib` vs others) — and the `ALSA_PLUGIN_DIR` result above suggests the bundled `libasound` would not honour it anyway. Not bundling the library sidesteps the guesswork entirely.

**Rejected: freezing on each target distribution.** Correct in principle, and it is exactly why the locally-built sidecar works here, but it multiplies the release matrix by every distribution we claim to support.

### 2. Resolve the microphone in one shared place, and degrade instead of exiting

`transcriber.py` repeats the same block at three call sites — `:754` (Linux dual-capture), `:1008` (WASAPI), `:1246` (macOS tap): try `sd.query_devices(kind='input')`, and on any exception print `⚠️ Could not auto-detect microphone` and `return 1`. The fix goes into one helper that all three call, so the behaviour cannot drift between platforms and the next capture path added gets it for free.

Behaviour, per the spec deltas: when there is no resolvable default input, pick the first device reporting input channels and name it in the output; when there is no such device at all, report that clearly, name `--list-devices` and `--mic-device`, and exit non-zero. An explicitly specified bad device keeps aborting exactly as it does today — that is a user error, not a detection failure, and the `audio-capture` delta keeps the two separate.

### 3. Declare the ALSA runtime dependency on the packages

Once the library is no longer bundled, the packages depend on the host having it. Add the ALSA soname to `bundle.linux.rpm.depends` beside the existing two, and confirm the `.deb`'s generated dependencies include it. The AppImage has no dependency mechanism and simply relies on the host, which is how AppImages are expected to treat the audio and graphics stacks — and is what `fix-appimage-egl-crash` already established for the graphics half.

### 4. Verify on a distribution that is not the build host

The whole bug is invisible on Debian/Ubuntu, where the build and run layouts coincide: a `.deb` test alone would have shown nothing wrong. So the primary verification is a CI-built `.rpm` on Fedora, with the `.deb` checked only to prove no regression. This mirrors why the bug survived earlier testing — the Linux live-capture verification that passed was run against a locally-built (Fedora-frozen) sidecar.

## Risks / Trade-offs

- **[Risk]** The host lacks `libasound`. → It is present on every desktop Linux that has working audio; the packages now declare it, and `libwebkit2gtk`/`libgtk-3` are already required the same way.
- **[Risk]** A host's `libasound` is *older* than the one PortAudio was built against. → The ALSA 1.x ABI has been stable for years, and Ubuntu 22.04's build target is older than the distributions being fixed, so the realistic direction is host-newer.
- **[Risk, unexplained]** The AppImage asymmetry. The user's 08:41 AppImage run auto-detected `HDA Intel PCH: ALC257 Analog (hw:0,0)` and transcribed live, while every run here of that same binary — including from inside the mounted AppImage, sandbox disabled — sees zero inputs. No mechanism has been found for this. If the visible device set varies over time (PortAudio's ALSA backend omits devices it cannot open, so a suspended or busy analog codec could come and go), then Decision 1 alone might not be sufficient in all states, which is precisely why Decision 2 ships with it rather than after it. **Do not treat Decision 1 as proven sufficient on the strength of one successful preload test.**
- **[Trade-off]** Decision 2 makes a previously fatal condition non-fatal, so a user could get a session on an unexpected device instead of an error. Mitigated by naming the chosen device in the output, and it is strictly better than the current behaviour of exiting with no usable alternative offered.
- **[Trade-off]** A committed `.spec` is more build machinery than a CLI invocation, and the spec must stay in step with the flags it replaces (icon, add-data, paths). Accepted because no CLI route to binary exclusion exists.

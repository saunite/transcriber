## Context

Windows live capture works via `wasapi_capture.py` (`WASAPICapture`), which wraps `pyaudiowpatch` to open a WASAPI loopback stream, reads int16 PCM on a background thread, converts to float32 mono, and pushes chunks through a queue to a callback. `transcriber.py` selects this path when `--wasapi` is passed. Linux live capture works through the existing `sounddevice`-based `AudioCapture` (`audio_capture.py`), auto-detecting a PulseAudio/PipeWire monitor source. Both give "no extra software" system-audio capture that works with Bluetooth output devices.

macOS has no equivalent today. `sounddevice`/PortAudio on macOS can only capture from CoreAudio *input* devices — there is no PortAudio-level API for tapping arbitrary system output, which is exactly the gap WASAPI loopback and PulseAudio monitor fill on the other two platforms. Getting the same "just works, no extra driver" experience on macOS requires a macOS-specific system API that PortAudio doesn't expose.

**Authoring constraint**: this design is written without macOS hardware available to validate against. Every native-API decision below is based on Apple's published API surface, not on tested behavior. This is called out explicitly wherever it matters, with a fallback that doesn't share that risk.

## Goals / Non-Goals

**Goals:**
- Native, no-virtual-driver system-audio capture on macOS, matching the "just works with Bluetooth" experience `--wasapi` gives on Windows.
- Reuse the existing `*_capture.py` module shape (`get_default_loopback_device`, `capture_stream`, `cleanup`) so `transcriber.py`'s call sites need minimal branching.
- A working macOS live-capture path exists even before the native tap is hardware-validated (the virtual-driver fallback via existing `--live` simple mode).
- Explicit, non-silent handling of macOS-version-too-old and permission-denied states.

**Non-Goals:**
- Supporting macOS versions before 14.4 with the native tap (Process Tap API doesn't exist there — the virtual-driver fallback covers this case instead, not a second native implementation).
- Bundling this into the Tauri GUI installer (`add-tauri-gui`) — that's a follow-up once this is hardware-validated.
- Screen recording / video capture of any kind — audio only.

## Decisions

### 1. Core Audio Process Tap API over ScreenCaptureKit
Two Apple APIs can capture system audio: `ScreenCaptureKit`'s `SCStream` (audio-capable since macOS 13) and the Core Audio **Process Tap API** (`AudioHardwareCreateProcessTap`, macOS 14.4+).

Process Tap is chosen because it's purpose-built for exactly this (audio-only, no screen-recording infrastructure involved) and its permission prompt is scoped to audio capture rather than the broader, more alarming "Screen Recording" permission ScreenCaptureKit requires even for an audio-only use case. The cost is a higher minimum OS version (14.4 vs 13.0).

**Alternative considered**: ScreenCaptureKit. Rejected primarily for the misleading Screen Recording permission prompt on an app that never touches video — a bad first-run experience for a meeting-transcription tool. Revisit if 14.4 adoption or Process Tap reliability turns out to be a problem once testable.

### 2. Native helper subprocess, not PyObjC bindings in Python
Neither API is reachable from pure Python/PortAudio. Two ways to bridge:
- **(a)** A small native Swift/Objective-C command-line helper that opens the tap and writes raw PCM frames to stdout, invoked as a subprocess.
- **(b)** PyObjC bindings called directly from `macos_capture.py`.

Going with **(a)**. It mirrors a pattern already in this codebase (`audio_extractor.py` already shells out to the `ffmpeg` binary and reads its output), keeps all Core Audio/permission-handling complexity in a small, independently buildable/testable native binary, and avoids adding a PyObjC dependency to the Python engine for something only macOS needs. `macos_capture.py` spawns the helper, reads raw PCM chunks from its stdout on a background thread (same shape as `WASAPICapture._read_loop`), and converts to float32 mono for the existing pipeline — `transcriber.py`'s call sites don't need to know a subprocess is involved.

**Alternative considered**: PyObjC. Rejected — larger new dependency surface, ctypes-adjacent fragility, and no reuse of an existing pattern in this codebase.

### 3. New `--coreaudio-tap` flag, not overloading `--wasapi`
`--wasapi` is a Windows-specific term (an actual Windows API name) and today's code imports `wasapi_capture` unconditionally when it's set. Rather than overload that flag cross-platform, add `--coreaudio-tap` (macOS-only) as its direct analogue — same role, platform-appropriate name, zero risk to existing Windows/Linux flag behavior. `transcriber.py` gains one new branch (`elif args.coreaudio_tap: transcribe_live_coreaudio_tap(...)`) alongside the existing `--wasapi` branch; both raise a clear error if used on the wrong OS.

### 4. Fallback path ships unconditionally, independent of tap validation
The existing `--live` simple/sounddevice path already works on macOS today for any CoreAudio input device — including a virtual loopback device (BlackHole, Loopback, or similar) if the user installs one, exactly like Windows' Stereo-Mix-or-VB-Cable fallback already documented in the README. This requires **zero new code** — it's the existing `transcribe_live_simple` path. This proposal documents it explicitly as the macOS fallback so that a working (if less convenient) macOS live-capture path exists regardless of how the native tap validation goes.

### 5. Explicit failure states, not silent degradation
The native helper and `macos_capture.py` must distinguish and surface three distinct failure modes rather than a generic error:
- **OS too old** (< 14.4): detected before spawning the helper (via `platform.mac_ver()`), fails fast with a message pointing at the fallback.
- **Permission not granted**: the helper's tap-creation call fails with a permission error; surfaced as "grant audio capture permission in System Settings > Privacy" rather than a generic capture failure.
- **Tap creation fails for another reason**: surfaced with the underlying error, falling back is suggested but not automatic (auto-falling-back to a different capture mode on error is more surprising than helpful for a live meeting tool).

## Risks / Trade-offs

- **[Risk]** The entire native-tap implementation is unvalidated on real hardware as of authoring — Apple's Process Tap API could behave differently than documented (sample format, stream lifecycle, permission prompt timing). **Mitigation**: task list (see tasks.md) separates code-complete work from a dedicated hardware-validation pass; the fallback path is documented and works today without any of this new code, so macOS users aren't blocked while validation is pending.
- **[Risk]** A PyInstaller-frozen executable (relevant once this feeds into `add-tauri-gui`) may not carry the bundle identity/Info.plist entries macOS's privacy permission system expects, causing the permission prompt to misbehave or the grant to not persist. **Mitigation**: flagged as an open question below; validate specifically in the context of a proper `.app` bundle (which the Tauri build already produces) rather than a bare frozen binary, before wiring into the GUI.
- **[Risk]** Swift/Objective-C is a new language in this codebase's toolchain (previously pure Python + shell). **Mitigation**: the helper is intentionally small and single-purpose (open tap, write PCM to stdout); all audio processing/resampling logic stays in the existing, well-tested Python path.
- **[Trade-off]** Minimum macOS version of 14.4 for the native path excludes a meaningful slice of still-supported macOS releases. Accepted because the fallback path covers them without a second native implementation to maintain.

## Open Questions

- Does the Process Tap permission grant require the requesting binary to live inside a proper `.app` bundle with the relevant Info.plist keys, or does a bare CLI binary work? Needs real-hardware testing; affects whether this capability works standalone via the CLI at all, or only once wired into the (bundled, `.app`-packaged) Tauri GUI.
- What's the exact sample format/channel layout the tap delivers (interleaved stereo int16/float32, sample rate)? Assumed similar to WASAPI's shape for this design; needs confirmation once testable, may change the resampling step in `macos_capture.py`.
- Should the native helper be a universal binary (arm64 + x86_64) from the start, or arm64-only initially given current Mac hardware? Assumed universal for broadest compatibility; confirm build tooling supports this without hardware to test the x86_64 leg.

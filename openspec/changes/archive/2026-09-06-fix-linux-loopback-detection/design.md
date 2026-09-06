## Context

See proposal.md - Why for the root cause. Confirmed concretely on this machine:
- `pactl get-default-sink` → `alsa_output.pci-0000_00_1f.3.analog-stereo`
- `pactl list sources short` → `alsa_output.pci-0000_00_1f.3.analog-stereo.monitor` (real monitor, `PipeWire`, `s32le 2ch 48000Hz`)
- `parec --device=<that name> --format=s16le --rate=16000 --channels=1` while `espeak-ng | paplay` played speech → real, non-zero audio energy captured directly at 16kHz mono, no manual resampling needed. `parec` asks the PipeWire/PulseAudio server itself to do the rate/channel conversion — it isn't a dumb byte pipe.
- Every `sounddevice`-visible device (`pipewire`, `default`, the JACK bridge) captured pure silence in the identical test.

`wasapi_capture.py` and `macos_capture.py` already establish the pattern for "OS-native loopback capture, not exposed through generic device enumeration": spawn/call the native mechanism, read on a background thread, push chunks to a queue, and expose a `capture_stream(callback, device_index, verbose)` + `get_default_loopback_device()` + `cleanup()` shape that `transcriber.py`'s live-capture functions already know how to drive.

## Goals / Non-Goals

**Goals:**
- Linux system-audio loopback (both `transcribe_live_simple`'s single-source path and `_transcribe_live_linux_dual`'s dual-source path) captures the real monitor signal, verified with actual non-silent audio.
- Match the existing native-capture shape (`wasapi_capture.py`/`macos_capture.py`) so `transcriber.py`'s call sites change minimally and predictably.
- No new Python dependency: `pactl` and `parec` (`pulseaudio-utils`, or PipeWire's own `pipewire-pulse` compatibility layer) are already assumed present by this codebase's existing Linux setup instructions (`setup_loopback_instructions()` already tells users to run `pactl list sources`).

**Non-Goals:**
- Fixing or replacing `AudioCapture`'s Windows loopback branch (Stereo Mix/Wave Out scanning) - untouched, unrelated to this bug.
- Adding a `pw-record`/native-PipeWire-protocol implementation. `parec` already works transparently against both real PulseAudio and PipeWire's `pipewire-pulse` compatibility server (confirmed above), so there's no reason to depend on PipeWire's own protocol/library.
- Changing the explicit `--audio-device N` override path. If a user already passes a specific `sounddevice` index, that continues to mean exactly what it means today (a `sounddevice` device, opened via `sounddevice`) - this fix only replaces what happens on *auto-detect* (`--audio-device` left at its default `-1`) on Linux.

## Decisions

**New module `linux_loopback_capture.py`, not a patch inside `audio_capture.py`.** Mirrors `wasapi_capture.py`/`macos_capture.py`: a `LinuxLoopbackCapture` class with `get_default_loopback_device()` (returns the discovered monitor source name + a sample-spec dict, or `None`), `capture_stream(callback, device_index=None, verbose=False)`, and `cleanup()`. Keeping it a separate module/class (rather than growing `AudioCapture` with a third capture mechanism) matches how this codebase already isolates each OS-native mechanism into its own file, and leaves `AudioCapture` (still used for Windows' non-WASAPI fallback, and for Linux's explicit-device-index override) alone.

**Discovery: `pactl get-default-sink` + `pactl list sources short`, plain text parsing - no `pactl -f json`.** Two subprocess calls, tab-split parsing (`pactl list sources short` is already tab-separated: id/name/driver/samplespec/state). `<default-sink-name>.monitor` is checked against the source list first (matches the *current* default output, mirroring WASAPI's own "match the default output's loopback variant, else take the first" logic); if the default-sink lookup fails or that name isn't present, fall back to the first source name found ending in `.monitor`. If `pactl` isn't on `PATH` at all, or no monitor source is found, `get_default_loopback_device()` returns `None` - same "could not auto-detect" contract callers already handle.

**Capture: spawn `parec --device=<name> --format=s16le --rate=16000 --channels=1`, read raw stdout in a background thread.** Requesting 16kHz mono *directly from `parec`* means the server does the resampling, so `transcriber.py` never needs a manual `scipy.signal.resample` step for the Linux loopback side at all - unlike WASAPI (fixed-rate native API, resampled in Python) and Core Audio Tap (native tap rate unknown until capture starts, resampled in Python), PulseAudio/PipeWire's client protocol supports arbitrary output rate/channels natively. This also **removes the `ZeroDivisionError`-guard/`transform_sys` resampling code added in `add-linux-dual-source-live-capture`'s `_transcribe_live_linux_dual`** for the sys side - dead code once this lands, since there's nothing left to resample. The background thread reads fixed 1024-frame blocks (`os.read` in a loop, same `chunk_size = 1024` convention `wasapi_capture.py` uses) and pushes them as float32 mono numpy arrays (`int16 / 32768.0`) to a queue; `capture_stream`'s main-thread loop drains the queue with a short timeout and calls `callback(chunk)` synchronously in the main thread - same shape as `WASAPICapture.capture_stream`, so `KeyboardInterrupt` raised from inside a caller's callback (e.g. a silence-timeout check) propagates and stops the loop correctly, without the polling-loop workaround `_transcribe_live_linux_dual` currently uses to route around `sd.InputStream`'s callback running on PortAudio's own thread.

**`transcribe_live_simple` and `_transcribe_live_linux_dual` both gain a `platform.system() == "Linux" and device_id is None` branch that uses `LinuxLoopbackCapture` instead of `AudioCapture`/a raw `sd.InputStream` for the *system-audio* side only.** The microphone side in `_transcribe_live_linux_dual` stays exactly as `add-linux-dual-source-live-capture` left it (plain `sd.InputStream`, cross-platform, unaffected by this bug). An explicit `--audio-device N` on Linux keeps today's exact `sounddevice`-index behavior - out of scope per Non-Goals.

## Risks / Trade-offs

- [Depends on `pactl`/`parec` being on `PATH`] → Mitigation: both ship in `pulseaudio-utils` (or are provided by PipeWire's own `pipewire-pulse` package) on essentially every desktop Linux distribution that also ships PipeWire/PulseAudio, which this codebase already assumes (its own `setup_loopback_instructions()` already tells users to run `pactl`). If missing, `get_default_loopback_device()` returns `None` and the existing "could not auto-detect loopback device" error path fires - no crash, no silent wrong behavior.
- [A monitor source can report `SUSPENDED` state until something reads from it] → Pre-existing, already-documented cold-start behavior (see `add-linux-dual-source-live-capture` design.md); `parec` opening the stream is itself "something reading from it," so this resolves the same way it already does for `pactl`-based manual testing.
- [`parec`'s own resampling quality/latency vs. `scipy.signal.resample`] → Not a new risk: this is the same resampling job, just done server-side instead of client-side; PulseAudio/PipeWire's resampler is what every other audio application on the system already relies on.

## Context

`transcribe_live_wasapi` (`transcriber.py`) already implements the full dual-source pattern this change needs: two independent capture streams, thread-safe queues drained by a worker thread, resampling to the 16kHz target rate, per-source WAV files, `[SYS]`/`[MIC]`-tagged output lines, and (via `drop-ffmpeg-dependency`'s `_merge_sys_mic_wav`) a merged stereo WAV when `--save-audio` is set. Its only Windows-specific piece is *how it acquires the system-audio stream* — `WASAPICapture`/`pyaudiowpatch`, needed because standard PortAudio device enumeration doesn't expose Windows loopback devices without that extension. Everything else in the function (the mic side, the queues, the tagging, the merge) already uses plain `sounddevice`, which works identically on Linux.

On Linux, the system-audio side needs no platform-specific library at all: PulseAudio/PipeWire already exposes the monitor as an ordinary PortAudio input device, and `audio_capture.py`'s `AudioCapture.get_loopback_device()` already auto-detects it (this is exactly what `transcribe_live_simple`'s existing system-audio-only path already uses).

## Goals / Non-Goals

**Goals:**
- Linux `--live --include-mic` (no `--wasapi`/`--coreaudio-tap`) produces the same `[SYS]`/`[MIC]`-tagged output, WAV files, and merge behavior as the Windows path.
- Verify this end-to-end on real hardware in this environment (a real mic and a real PipeWire monitor source are both present and confirmed working).

**Non-Goals:**
- Refactoring `transcribe_live_wasapi` and `transcribe_live_coreaudio_tap` to share a common dual-capture core with the new Linux path. See Decisions below for why this is deliberately deferred rather than done here.
- Any change to the Windows or macOS capture paths themselves.

## Decisions

**Duplicate the WASAPI dual-capture structure into `transcribe_live_simple`, rather than extracting a shared core first.** The obviously "cleaner" version of this change would factor the queue/tagging/merge machinery that `transcribe_live_wasapi` and `transcribe_live_coreaudio_tap` already both implement into one platform-agnostic function, parameterized only by how each platform acquires its system-audio stream — reducing three large near-duplicate blocks to one. That refactor is deliberately **not** done here: it would touch two already-working, hardware-verified live-capture paths (Windows and macOS) with no Windows or macOS hardware in this environment to re-verify they still work afterward. This change instead ports the pattern into a third, additive block scoped entirely to the new Linux branch — the existing Windows and macOS code is not touched at all. The duplication this leaves behind is real and worth revisiting once a change can actually verify all three platforms together; it is not free, just the safer trade given what can and can't be tested from here.

**System-audio acquisition swaps to `AudioCapture.get_loopback_device()` + a plain `sd.InputStream`, reusing what `transcribe_live_simple` already does for its single-source path.** No new dependency, no new device-detection logic — the existing auto-detect (with its existing "could not auto-detect loopback" error path) is reused as-is for the dual-source branch too.

**The mic-side code (device resolution, channel detection, resampling, WAV writing) is copied from `transcribe_live_wasapi` near-verbatim.** It is already platform-generic (`sounddevice`, no WASAPI-specific calls) — the only reason to duplicate rather than call into it directly is that it's currently inline in a large function rather than factored out, which is exactly the duplication accepted above rather than fixed now.

## Risks / Trade-offs

- [Duplicating ~150-200 lines of queue/tagging/merge logic into a third call site] → Accepted per the Decisions section above; flagged explicitly rather than silently left as unexplained copy-paste, so a future change can do the three-way refactor once Windows/macOS hardware is available to verify it.
- [PipeWire's monitor source can appear "SUSPENDED" until something starts reading from it — a cold-start edge case] → Mitigation: this is pre-existing behavior of the already-shipped system-audio-only Linux path (same `get_loopback_device()` call), not new risk introduced by this change.

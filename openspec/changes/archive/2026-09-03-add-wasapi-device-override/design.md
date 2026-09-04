## Context

See proposal.md - Why. `WASAPICapture.get_default_loopback_device()` (`wasapi_capture.py`) already auto-detects by name-matching against the default output device, with a "first loopback device found" fallback. `transcriber.py`'s `--audio-device` flag already lets the CLI bypass auto-detection entirely (`device_index = args.audio_device` when `>= 0`); this design only needs to reach that existing flag from the GUI, plus fix the misleading remedy text.

## Goals / Non-Goals

**Goals:**
- An escape hatch exists for the (currently unconfirmed) case where auto-detection picks the wrong device.
- The override is visibly, explicitly discouraged — not presented as an equally-valid everyday choice.
- The CLI's failure-path error message stops recommending a remedy that cannot work.

**Non-Goals:**
- A device *listing* UI (dropdown of available WASAPI loopback devices) — see proposal.md's "Deliberately not building." A raw numeric override is the whole surface here.
- Any change to `wasapi_capture.py`'s auto-detection logic itself.
- Extending `list_devices`/`list_devices_json` to include loopback devices — that's exactly the device-listing feature being deferred.

## Decisions

**Raw numeric input, not a dropdown.** A dropdown implies "here are your real choices, pick one" — exactly the wrong framing for a field meant to be avoided. A blank-by-default numeric input, paired with the warning text, better matches "you shouldn't normally touch this." Also the lazier build: no new backend enumeration, no new Rust response shape, no new device-index-space bookkeeping to keep separate from the microphone list.

**Omit `--audio-device` entirely when unset, don't pass a sentinel.** Mirrors how `--mic-device` is already handled (`if let Some(dev) = mic_device`) — `transcriber.py`'s own default (`args.audio_device` defaults to `-1`, `if args.audio_device >= 0`) is preserved untouched; the GUI change is additive, not a reimplementation of the CLI's default logic.

**Fix the error message to drop the `--list-devices` suggestion, not to add a working one.** The honest fix given this change's Non-Goals: `transcriber.py`'s "Run with --list-devices to see available devices" (line ~673) becomes something that doesn't point at a list that can't help — e.g. suggesting the new override field exists, or just stating no loopback device was found without prescribing a specific remedy. Building a real "here's how to find your device index" flow is exactly the deferred device-listing feature.

## Risks / Trade-offs

- [A user finds the override field and uses it as a first resort rather than a last resort, despite the warning] → Mitigation: field is unlabeled as a dropdown of "choices," blank by default, and the warning text is explicit and unconditional, not just a tooltip.
- [Without a device list, a user who does need to override has no easy way to find the right index] → Accepted per Non-Goals; the override exists for troubleshooting with developer/support guidance, not for self-service discovery. Revisit if this proves to be a real, common need.

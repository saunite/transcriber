## 1. Verify how to follow the default

- [ ] 1.1 **Ask the user first:** this redirects system audio for a few seconds. With their go-ahead, run a one-off script (in the scratchpad, not committed) that:
  1. records the current default sink;
  2. loads two `module-null-sink`s, A and B, and sets A as default;
  3. starts `parec --device=@DEFAULT_MONITOR@ --format=s16le --rate=16000 --channels=1`;
  4. plays a generated 440 Hz tone into A with `pacat`, then sets B as default and plays an 880 Hz tone into B;
  5. checks which tones reached the recording;
  6. restores the original default sink and unloads both modules, even on failure.

  Record under this task whether the 880 Hz tone arrived after the switch. That decides design.md Decision 1 (it did) or Decision 2 (it didn't).

  Verify the default sink afterwards is the recorded original and no null sinks remain (`pactl list sinks short`).

## 2. Tests first

- [ ] 2.1 Add a root `test_linux_loopback_capture.py` with `subprocess.Popen` and `subprocess.run` faked:
  - **If 1.1 chose Decision 1:** assert `capture_stream` starts `parec` with `--device=@DEFAULT_MONITOR@` when auto-detecting, and still with the given name when one is passed explicitly.
  - **If 1.1 chose Decision 2:** fake `pactl get-default-sink` returning A and then B. Assert a second `parec` is started on `B.monitor`, the first is terminated, and chunks from both reach the callback without capture ending.

  Verify it fails against today's `linux_loopback_capture.py`.

## 3. Fix

- [ ] 3.1 Implement the decision chosen in 1.1 in `linux_loopback_capture.py`, and in `transcriber.py`'s Linux auto-detect `run_sys` only if the device argument changes. Keep the start-up monitor check and the status-line name.

  Verify 2.1 passes, and `test_dual_capture.py` and the e2e Linux suite still pass.

- [ ] 3.2 Re-run the 1.1 null-sink script against the real capture: `LinuxLoopbackCapture.capture_stream` with the tones, with the user's go-ahead again. Verify the 880 Hz tone arrives after the switch and the original default sink is restored.

## 4. Docs, backlog and verification

- [ ] 4.1 README Linux notes: system audio follows the default output device during a session. Verify it's described.

- [ ] 4.2 `openspec/backlog.md`: reword D6 to its Windows half only (the WASAPI default-loopback match), noting `03-fix-audit-edges-windows`. Verify the Linux half no longer appears.

- [ ] 4.3 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub, and verify it exits 0.

- [ ] 4.4 **Manual check, by the user, on a rebuilt sidecar:** start a live session in the app while audio plays on the laptop speakers, then switch output (for example connect the Bluetooth headphones) mid-session, keeping nothing afterwards. Verify system-audio lines keep arriving after the switch.

## 1. Verify how to follow the default

- [x] 1.1 **Ask the user first:** this redirects system audio for a few seconds. With their go-ahead, run a one-off script (in the scratchpad, not committed) that:
  1. records the current default sink;
  2. loads two `module-null-sink`s, A and B, and sets A as default;
  3. starts `parec --device=@DEFAULT_MONITOR@ --format=s16le --rate=16000 --channels=1`;
  4. plays a generated 440 Hz tone into A with `pacat`, then sets B as default and plays an 880 Hz tone into B;
  5. checks which tones reached the recording;
  6. restores the original default sink and unloads both modules, even on failure.

  Record under this task whether the 880 Hz tone arrived after the switch. That decides design.md Decision 1 (it did) or Decision 2 (it didn't).

  Verify the default sink afterwards is the recorded original and no null sinks remain (`pactl list sinks short`).

  **Done 2026-09-15**, with the user's go-ahead. The script is `follow_default.py` in the scratchpad. The system runs PulseAudio on PipeWire 1.6.8, with WirePlumber 0.5.14 and `linking.follow-default-target = true`. Four runs; "after switch" is the 880 Hz peak-to-median ratio in the recording:

  | parec device | default switched to B | after switch | parec attached to after the switch |
  |---|---|---|---|
  | `@DEFAULT_MONITOR@` | yes | 9724 (received) | not printed |
  | `follow_test_a.monitor` | yes | 9968 (received) | not printed |
  | `follow_test_a.monitor` | no | 24 (noise) | A's monitor (`target.object = "follow_test_a"`) |
  | `follow_test_a.monitor` | yes | 9724 (received) | **B's monitor** (id 2681), though `target.object` still reads `follow_test_a` |

  **Finding:** on PipeWire with WirePlumber's default policy, a recording connected to the monitor of the sink that is the default at the time follows the default when it changes. That holds with the explicit `<sink>.monitor` name today's code passes. The no-switch run rules out the tone reaching A's monitor any other way. So D6's Linux half doesn't reproduce here: today's code already meets the new scenario on PipeWire, and `@DEFAULT_MONITOR@` behaves the same.

  **Not verified:** PulseAudio proper, and WirePlumber with `linking.follow-default-target` off, can't be tested on this machine. Neither Decision 1 nor 2 has been proven necessary. Decision still to make: the apply paused to ask the user.

  **Afterwards:** the default sink is `alsa_output.pci-0000_00_1f.3.analog-stereo` (the original), and `pactl list sinks short` lists no test sinks.

## 2. Pin today's behaviour

- [x] 2.1 Add a root `test_linux_loopback_capture.py` with `shutil.which` and `subprocess.run` faked:
  - `pactl list sources short` lists `sink_a.monitor` first and `sink_b.monitor` second, and `pactl get-default-sink` returns `sink_b`: `get_default_loopback_device()` returns `sink_b.monitor`;
  - with no default sink reported, it returns the first monitor;
  - with `Popen` faked, `capture_stream(callback)` without a device starts `parec --device=sink_b.monitor`.

  Verify it passes, and that it fails when `get_default_loopback_device` is mutated to return the first monitor. That's the behaviour the follow-the-default result depends on.

  **Done 2026-09-15.** It passes. With the default-sink branch in `get_default_loopback_device` replaced by `pass`, so it falls through to the first monitor, the first assertion fails. The file was restored afterwards (no diff), and the test passes again.

## 3. Docs, backlog and verification

- [x] 3.1 README Linux notes: on PipeWire, system audio follows the default output device during a session (for example, when Bluetooth headphones connect), and on PulseAudio proper this is untested. Verify it's described.

  **Done 2026-09-15.** README "Linux" (audio setup) now says capture records the default output's monitor, follows a default change on PipeWire (for example Bluetooth headphones connecting), and is untested on PulseAudio itself.

- [x] 3.2 `openspec/backlog.md`:
  - reword D6 to its Windows half only (the WASAPI default-loopback match), noting `03-fix-audit-edges-windows`;
  - add to "Known limits, accepted for now": following the default output on Linux relies on WirePlumber's `linking.follow-default-target` (verified on PipeWire 1.6.8 and WirePlumber 0.5.14), and is untested on PulseAudio proper or with that setting off.

  Verify the Linux half of D6 no longer appears and the limit is listed.

  **Done 2026-09-15.** D6 now reads "D6 (Windows half)", recording that the Linux half didn't reproduce, and points at `03-fix-audit-edges-windows`. "Known limits, accepted for now" gains the PipeWire-only limit with the verified versions.

- [x] 3.3 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub, and verify it exits 0.

  **Done 2026-09-15.** With `TRANSCRIBER_TEST_SPEECH` set and GitHub reachable: 16/16 suites passed, exit 0, with nothing skipped. That's one more suite than before (`test_linux_loopback_capture.py`).

- [ ] 3.4 **Manual check, by the user:** in the current app build, start a live session while audio plays on the laptop speakers, then switch output mid-session (for example connect the Bluetooth headphones), keeping nothing afterwards. Verify system-audio lines keep arriving after the switch.

  **Not done (archived open, 2026-09-15).** The user chose to archive without this check. Following the default output is verified only by the null-sink script in task 1.1, not in the app itself, and no code changed in this change.

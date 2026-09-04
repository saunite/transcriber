# linux-sidecar-build

## Purpose
Requires the Linux `transcriber-sidecar` binary produced by `build_sidecar.py`/PyInstaller to actually run standalone, independent of whatever process built it (CI job, WSL build, or otherwise).

## Requirements

### Requirement: Frozen Linux sidecar runs standalone
The PyInstaller-frozen Linux `transcriber-sidecar` binary produced by `build_sidecar.py` SHALL run standalone on Linux and complete a file transcription without requiring a Python interpreter or the project's virtualenv on the target machine.

#### Scenario: Standalone file transcription
- **WHEN** the frozen Linux sidecar binary is invoked with `--file <sample clip> --model base --model-path <bundled model dir>`
- **THEN** it produces a transcript output file, exiting 0, with no dependency on a Python interpreter being installed on the host

#### Scenario: Device listing runs without crashing
- **WHEN** the frozen Linux sidecar binary is invoked with `--list-devices-json`
- **THEN** it exits 0 and prints valid JSON (an empty device array is an acceptable result on a host/container with no audio hardware exposed — this scenario only checks that it does not crash)

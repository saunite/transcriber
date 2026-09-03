# linux-sidecar-build

## Purpose
Defines the CI mechanism that freezes the Python transcription engine into a standalone Linux binary (via `build_sidecar.py`/PyInstaller) for bundling into the Tauri Linux build, and requires that mechanism to have actually run and been verified rather than assumed.

## Requirements

### Requirement: Frozen Linux sidecar runs standalone
The PyInstaller-frozen Linux `transcriber-sidecar` binary produced by `build_sidecar.py` SHALL run standalone on Linux and complete a file transcription without requiring a Python interpreter or the project's virtualenv on the target machine.

#### Scenario: Standalone file transcription
- **WHEN** the frozen Linux sidecar binary is invoked with `--file <sample clip> --model base --model-path <bundled model dir>`
- **THEN** it produces a transcript output file, exiting 0, with no dependency on a Python interpreter being installed on the host

#### Scenario: Device listing runs without crashing
- **WHEN** the frozen Linux sidecar binary is invoked with `--list-devices-json`
- **THEN** it exits 0 and prints valid JSON (an empty device array is an acceptable result on a host/container with no audio hardware exposed — this scenario only checks that it does not crash)

### Requirement: CI produces a verified Linux build
The `ubuntu-latest` job in `.github/workflows/build-gui.yml` SHALL complete successfully on a real GitHub Actions run, producing a Linux Tauri bundle that embeds the frozen sidecar from the requirement above.

#### Scenario: Workflow run passes
- **WHEN** `build-gui.yml` is triggered (via `workflow_dispatch` or a qualifying push)
- **THEN** the `ubuntu-latest` matrix job completes without error and uploads a `transcriber-gui-ubuntu-latest` artifact

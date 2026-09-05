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

### Requirement: Sidecar is built from an isolated virtualenv
`build_sidecar.py` SHALL refuse to run outside a Python virtualenv. On distros where numpy/scipy are system packages (e.g. Fedora, linked against FlexiBLAS), FlexiBLAS loads its actual math backend via `dlopen()` at runtime, which PyInstaller's static import analysis cannot see — the frozen binary ends up bundling the FlexiBLAS shim with no backend behind it, and aborts (SIGABRT) on first use. A virtualenv's pip-installed numpy/scipy wheels bundle their own BLAS statically, so this can't happen.

#### Scenario: Build attempted from system Python
- **WHEN** `build_sidecar.py` is run with a `sys.prefix` equal to `sys.base_prefix` (i.e. not inside a virtualenv)
- **THEN** it exits non-zero with an error explaining the FlexiBLAS risk, before invoking PyInstaller

#### Scenario: Build run from a virtualenv
- **WHEN** `build_sidecar.py` is run with `pip install -r requirements-linux.txt pyinstaller` installed into a dedicated `.venv`
- **THEN** the frozen binary's `--file` transcription completes and exits 0, with no BLAS-related abort

### Requirement: Frozen sidecar survives multiprocessing's resource-tracker relaunch
The sidecar's entry point SHALL call `multiprocessing.freeze_support()` before running its own logic. `multiprocessing.resource_tracker` relaunches itself by re-invoking `sys.executable` with `-c "<code>"`; in a frozen PyInstaller onefile build, `sys.executable` is the sidecar binary itself, so without `freeze_support()` that relaunch re-runs the whole application from scratch instead of the tracker code, and crashes on a circular import.

#### Scenario: Repeated file transcriptions through the frozen binary
- **WHEN** the frozen Linux sidecar binary runs a `--file` transcription
- **THEN** no `multiprocessing.resource_tracker` traceback or "process died unexpectedly, relaunching" warning appears in its output, across repeated runs

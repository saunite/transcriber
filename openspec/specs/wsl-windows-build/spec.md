## Purpose

Defines how the Windows desktop build — the mingw cross-compiled Tauri shell plus the PyInstaller-frozen Windows sidecar — runs from a WSL environment with no Docker container, including how it fails clearly when the Windows-Python interop step's prerequisite is unavailable.

## Requirements

### Requirement: Windows shell cross-compiles natively from WSL
The Tauri shell for Windows SHALL be buildable by running `cargo tauri build --target x86_64-pc-windows-gnu` directly in a WSL environment with the mingw cross-toolchain installed, with no Docker daemon or container involved.

#### Scenario: Cross-compiling from WSL
- **WHEN** `cargo tauri build --target x86_64-pc-windows-gnu` is run from a WSL shell with `rustup target add x86_64-pc-windows-gnu` and the mingw-w64 packages installed
- **THEN** it produces `transcriber-gui.exe` (and `WebView2Loader.dll` on this target) under the target-triple release directory, with no container spawned

### Requirement: Windows sidecar freezes via reachable Windows Python interop
The Windows sidecar binary SHALL be produced by running `build_sidecar.py` under a Windows Python interpreter reached from WSL, and the build process SHALL detect whether such an interpreter is reachable before attempting the freeze, failing with a clear, actionable message rather than a cryptic error when none is found.

#### Scenario: Windows Python reachable
- **WHEN** a Windows Python interpreter with the sidecar's dependencies installed is reachable from the WSL environment
- **THEN** `build_sidecar.py` runs under it and produces a working `transcriber-sidecar.exe`

#### Scenario: No Windows Python reachable
- **WHEN** the build process runs on a machine with no reachable Windows Python interpreter (e.g. a native Linux machine, not WSL)
- **THEN** the Windows sidecar freeze step fails immediately with a message explaining that a Windows Python interpreter is required, rather than crashing partway through or silently skipping the sidecar

### Requirement: Portable artifact assembly correctly targets Windows from WSL
`build_portable.py`, when given a Windows target triple, SHALL assemble the Windows portable artifact regardless of the host operating system it is invoked from.

#### Scenario: Assembling from a WSL (Linux-reporting) interpreter
- **WHEN** `build_portable.py --target x86_64-pc-windows-gnu` is run under a Python interpreter that reports the host as Linux (e.g. from WSL)
- **THEN** it assembles the Windows artifact (copying `transcriber-gui.exe`, `transcriber-sidecar.exe`, and the model into a zip), not the Linux artifact

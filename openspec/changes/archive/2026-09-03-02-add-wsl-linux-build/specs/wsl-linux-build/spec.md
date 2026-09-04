## Purpose

Defines how the Linux desktop build runs natively from a WSL (or any native Linux) environment, with no Docker container, so builds are not slowed or corrupted by cargo's working-set I/O crossing onto a Windows-mounted filesystem.

## ADDED Requirements

### Requirement: Native Linux build with no container
The Linux desktop artifact SHALL be buildable by running `cargo tauri build` directly in a WSL or native Linux environment with the required system packages installed, with no Docker daemon or container involved at any step.

#### Scenario: Building from WSL
- **WHEN** `cargo tauri build` is run from a WSL shell with the toolchain installed
- **THEN** it produces a Linux `.AppImage`, with no Docker container spawned at any point

### Requirement: Cargo build output stays off Windows-mounted filesystem paths
The Linux build SHALL keep cargo's `target/` working-set file I/O on a native Linux (ext4 or equivalent) filesystem, not on a Windows-mounted path (e.g. `/mnt/c/...` under WSL).

#### Scenario: Build output relocated
- **WHEN** a build is run from WSL with the target directory configured to a native-filesystem path
- **THEN** cargo's `target/` directory is written there, not under a Windows-mounted path

#### Scenario: Portable-artifact assembly finds the build output
- **WHEN** `build_portable.py` runs after a build that used a relocated `target/` directory
- **THEN** it locates the built binaries and bundle output correctly, with no manual copy step

### Requirement: Source checkout stays off Windows-mounted filesystem paths
The Linux build SHALL keep the repository checkout itself on a native Linux (ext4 or equivalent) filesystem, not on a Windows-mounted path — relocating `target/` alone is not sufficient, since cargo reads source files (`Cargo.toml`, `Cargo.lock`, every `*.rs` file) and Tauri writes generated files (`src-tauri/gen/`) at wherever the checkout lives, on every build, independent of where `target/` is configured.

#### Scenario: Checkout on a Windows-mounted path
- **WHEN** the repository checkout itself is on a Windows-mounted path (e.g. `/mnt/c/...` under WSL), even with `target/` relocated to a native filesystem
- **THEN** the build still performs Windows-filesystem I/O for source reads and generated-file writes, and this requirement is not satisfied

#### Scenario: Checkout on a native filesystem
- **WHEN** the repository checkout is on a native Linux filesystem (e.g. `~/repos/<name>` under WSL)
- **THEN** the build performs no I/O against a Windows-mounted filesystem at any point

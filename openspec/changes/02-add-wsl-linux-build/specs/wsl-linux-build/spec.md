## Purpose

Defines how the Linux desktop build runs natively from a WSL (or any native Linux) environment, with no Docker container, so builds are not slowed or corrupted by cargo's working-set I/O crossing onto a Windows-mounted filesystem.

## ADDED Requirements

### Requirement: Native Linux build with no container
The Linux desktop artifact SHALL be buildable by running `cargo tauri build` directly in a WSL or native Linux environment with the required system packages installed, with no Docker daemon or container involved at any step.

#### Scenario: Building from WSL
- **WHEN** `cargo tauri build` is run from a WSL shell with the toolchain installed
- **THEN** it produces a Linux `.AppImage`, with no Docker container spawned at any point

### Requirement: Cargo build output stays off Windows-mounted filesystem paths
The Linux build SHALL keep cargo's `target/` working-set file I/O on a native Linux (ext4 or equivalent) filesystem, not on a Windows-mounted path (e.g. `/mnt/c/...` under WSL), regardless of where the source checkout itself is located.

#### Scenario: Repo checked out under /mnt/c
- **WHEN** the repository is checked out on a Windows-mounted path and a build is run from WSL
- **THEN** cargo's `target/` directory is written to a path on the native Linux filesystem, not under the mounted checkout

#### Scenario: Portable-artifact assembly finds the build output
- **WHEN** `build_portable.py` runs after a build that used a relocated `target/` directory
- **THEN** it locates the built binaries and bundle output correctly, with no manual copy step

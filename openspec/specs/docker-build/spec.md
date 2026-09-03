# docker-build

## Purpose
Defines how the Docker-based cross-compile build (`docker/build.ps1`) uses the build container's filesystem, so builds are not slowed or corrupted by bind-mounting the host source tree or `target/` directory across the Windows/Linux boundary.

## Requirements

### Requirement: Native-filesystem build inside the container
The Docker-based cross-compile build (`docker/build.ps1`) SHALL keep all `cargo`/`makensis` working-set file I/O on the build container's native Linux filesystem, and SHALL NOT bind-mount the host source tree or the `cargo` `target/` directory from the Windows host during the build.

#### Scenario: Building from a Windows checkout
- **WHEN** `docker/build.ps1` is run from a Windows host with the repo checked out on NTFS
- **THEN** the container builds against a copy of the source on its own native filesystem, not a live bind mount of the NTFS checkout

### Requirement: Only the build output crosses the host/container boundary
After a successful build, the process SHALL copy just the produced installer bundle back to the host filesystem, rather than exposing the entire build tree via a bind mount.

#### Scenario: Retrieving the installer
- **WHEN** the Windows NSIS build completes inside the container
- **THEN** the resulting installer bundle is copied out to the same host-side path (`src-tauri/target/x86_64-pc-windows-gnu/release/bundle/`) that the previous bind-mount-based build produced it at, so downstream steps (install/test) need no changes

#### Scenario: Build failure leaves no leaked container
- **WHEN** the build fails inside the container
- **THEN** the build script still removes the container before exiting, leaving no stopped containers accumulating across repeated runs

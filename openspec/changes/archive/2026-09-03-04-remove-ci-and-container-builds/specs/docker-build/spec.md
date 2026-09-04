## REMOVED Requirements

### Requirement: Native-filesystem build inside the container
**Reason**: The Docker-based cross-compile build has been removed entirely — all development now happens on a Linux/WSL machine that runs `cargo`/`rustc` natively, with no container involved. The underlying concern (keep cargo's working-set I/O off a Windows-mounted filesystem) is carried forward by `wsl-linux-build`'s and `wsl-windows-build`'s own filesystem requirements, not by this one.
**Migration**: See `openspec/specs/wsl-linux-build/spec.md` ("Cargo build output stays off Windows-mounted filesystem paths") for the WSL-native equivalent.

### Requirement: Only the build output crosses the host/container boundary
**Reason**: There is no longer a container, so there is no host/container boundary for build output to cross.
**Migration**: Not applicable — a native WSL build writes its output directly to the working filesystem; no copy-out step exists or is needed.

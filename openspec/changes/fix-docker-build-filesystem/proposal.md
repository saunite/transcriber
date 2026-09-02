## Why

The Windows Tauri build (`docker/build.ps1`) bind-mounts the repo straight from NTFS into the Linux build container (`-v "${PWD}:/app"`). Every file `cargo build` touches for incremental compilation, and every byte `makensis` reads/writes while packaging the ~260MB installer, crosses Docker Desktop's cross-OS filesystem bridge. That bridge is slow for many-small-file and large-file I/O alike (see [Microsoft's WSL filesystem performance guidance](https://learn.microsoft.com/en-us/windows/wsl/filesystems#file-storage-and-performance-across-file-systems)), and cross-filesystem mtime handling likely also defeats cargo's incremental-build cache between runs. A single Windows installer build currently takes on the order of 40-50 minutes; most of that is filesystem-bridge overhead, not actual compilation or compression work.

## What Changes

- `docker/tauri-build.Dockerfile` / `docker/build.ps1`: copy the repo into the container's native Linux filesystem (a Docker volume or an image `COPY` layer) instead of bind-mounting the Windows checkout at `/app`.
- Run `cargo tauri build` entirely against that native-filesystem copy, so `cargo`'s target directory and the resources being packaged by `makensis` never cross the NTFS bridge during the build.
- After the build, copy only the finished installer (and any other build artifacts the caller needs) back out to the Windows host — via `docker cp` or a narrow output-only bind mount — rather than mounting the whole project both ways.
- The cargo registry cache (already a named Docker volume) stays as-is; it was never the bottleneck.

## Capabilities

### New Capabilities
- `docker-build`: the Docker-based cross-compile process that produces the Windows installer when native Rust is unavailable on the host.

### Modified Capabilities
(none — desktop-gui's shipped behavior is unaffected; only how its Windows installer gets built changes)

## Impact

- Affected files: `docker/tauri-build.Dockerfile`, `docker/build.ps1`.
- No change to `src-tauri/`, `src/`, or `transcriber.py` — the app being built is unaffected, only how the Windows installer is produced.
- Anyone rebuilding the Windows installer locally (this is the only known path, since native `cargo`/`rustc` are blocked on this machine by an execution-policy restriction) should see materially faster builds and more reliable incremental rebuilds.

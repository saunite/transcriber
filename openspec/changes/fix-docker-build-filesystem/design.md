## Context

`docker/build.ps1` builds the Windows Tauri installer by bind-mounting the repo checkout from NTFS into a Linux container (`-v "${PWD}:/app"`) and running `cargo tauri build` against that mount. Both phases of the build are dominated by crossing that mount rather than by real work:

- `cargo build`: incremental compilation reads/writes thousands of small files in `src-tauri/target/`. Each touch crosses Docker Desktop's cross-OS filesystem bridge, and cross-filesystem mtime handling can make cargo re-do more incremental work than it should between runs.
- `makensis`: packages ~260MB of resources (dominated by the bundled 145MB Whisper model) into the NSIS installer. That data is read from, and the installer written to, the same slow bridge.

Native `cargo`/`rustc` are blocked on this Windows machine by a machine-level execution-policy restriction (see `sidecar.rs`/tasks.md history), so the Docker cross-compile path is the only way to produce the Windows installer here — it needs to stay usable, just not slow.

## Goals / Non-Goals

**Goals:**
- Keep all `cargo`/`makensis` file I/O on the container's native Linux filesystem for the duration of the build.
- Only cross the Windows/Linux boundary once per build, to hand back the finished installer(s).
- Preserve the existing cargo registry cache volume (already native-speed, not part of the problem).
- Keep `docker/build.ps1` a single, no-argument entry point (`.\docker\build.ps1`), as it is today.

**Non-Goals:**
- Not changing what gets built (Windows NSIS target, Linux appimage/deb once task 2.2's Linux sidecar exists) or any Rust/Python source.
- Not solving the native Windows Rust execution-policy block — Docker remains the build path.
- Not adding CI (`.github/workflows/build-gui.yml` already exists as a separate, still-unrun path).

## Decisions

**Copy the repo into the image instead of bind-mounting it.**
`docker/tauri-build.Dockerfile` gets a `COPY . /app` (after the existing toolchain-install layers) instead of relying on `build.ps1`'s bind mount for source. The container's `/app` is then plain container-filesystem, native-speed for both `cargo` and `makensis`.
- Alternative considered: bind-mount into a named Docker volume instead of an image `COPY`, then `cp` the host tree into the volume once before building. Rejected as more moving parts (still needs a copy step, but as a separate `docker run ... cp` instead of a Dockerfile layer) for no benefit — a `COPY` is simpler and Docker's build cache means unrelated re-builds (e.g. Dockerfile-only changes) don't re-copy needlessly.
- `.dockerignore` is added alongside the Dockerfile to keep `target/`, `node_modules/`, and other large/regeneratable directories out of the build context and the image.

**Copy the finished installer(s) back out with `docker cp`, not a second bind mount.**
`build.ps1` runs the build inside a *named* (non-`--rm`, or `--rm` after an explicit copy) container, then `docker cp <container>:/app/src-tauri/target/.../bundle ./src-tauri/target/.../bundle` to bring just the `bundle/` output directory back to the host, then removes the container.
- Alternative considered: mount only `src-tauri/target` from the host (leaving source `COPY`'d, only output bind-mounted). Rejected: `target/` is exactly where `cargo`'s incremental artifacts and `makensis`'s multi-hundred-MB read/write happen, so mounting it defeats the fix as much as mounting all of `/app` did.

**Cargo registry cache stays a named volume, unchanged.**
It was already native-speed and not implicated in the slowdown; no reason to touch it.

## Risks / Trade-offs

- [Image `COPY` means the build no longer sees uncommitted-but-unsaved editor state the instant it changes, unlike a live bind mount] → Not a real workflow loss here: this is a one-shot `.\docker\build.ps1` run against the current working tree, not a watch-mode dev loop; each invocation still picks up whatever's on disk at that moment.
- [`docker cp` after the build requires knowing the container ID/name, and forgetting `--rm` leaks stopped containers over repeated runs] → `build.ps1` names the container explicitly (e.g. `--name transcriber-tauri-build-run`) and removes it in a `finally`-equivalent (`docker rm -f` on both the success and failure paths).
- [Copying the whole repo into the image loses cargo's ability to reuse `target/` from a previous run if the image is rebuilt] → Unaffected: `target/` was never image-baked; it's produced fresh inside the running container each time, same as today, just on native filesystem.

## Migration Plan

1. Add `.dockerignore` (excludes `src-tauri/target`, `.git`, and other non-source directories from the build context).
2. Update `docker/tauri-build.Dockerfile`: add `COPY . /app` as the final layer, after the existing toolchain setup, with `WORKDIR /app`.
3. Update `docker/build.ps1`: drop the `-v "${PWD}:/app"` bind mount from `docker run`; run the build in a named container; `docker cp` the `bundle/` output directory back to the host afterward; remove the container.
4. Manually verify: run `.\docker\build.ps1`, confirm the installer lands at the same host path as before, and compare wall-clock time against the current ~40-50 minute baseline.

No rollback complexity — this only touches build tooling, not shipped product behavior; reverting the two files reverts the build path.

## Open Questions

- None — the approach is a direct application of the linked Microsoft guidance (native filesystem for the working set, cross the boundary once for the result).

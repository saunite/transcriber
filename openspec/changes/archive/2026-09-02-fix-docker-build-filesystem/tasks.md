## 1. Container-native build

- [x] 1.1 Add `.dockerignore` (excludes `src-tauri/target`, `.git`, and other non-source directories from the Docker build context)
- [x] 1.2 Update `docker/tauri-build.Dockerfile`: add `COPY . /app` (with `WORKDIR /app`) as the final layer, after the existing toolchain-install layers
- [x] 1.3 Update `docker/build.ps1`: drop the `-v "${PWD}:/app"` bind mount; run the build in a named (not `--rm`) container

## 2. Output handoff

- [x] 2.1 After a successful build, `docker cp` the container's `src-tauri/target/x86_64-pc-windows-gnu/release/bundle/` directory back to the same host-side path
- [x] 2.2 Remove the named container (`docker rm -f`) on both the success and failure paths, so repeated runs don't leak stopped containers

## 3. Verification

- [x] 3.1 Run `.\docker\build.ps1` end-to-end; confirm the installer lands at the same host path as before and installs/runs correctly

  Verified: installer builds and lands at `src-tauri/target/x86_64-pc-windows-gnu/release/bundle/nsis/Transcriber_0.1.0_x64-setup.exe` (247MB), installs silently with exit code 0, and the launched app is responsive. The chained native (Linux) `cargo tauri build` leg still fails as expected (`resource path 'binaries/transcriber-sidecar-x86_64-unknown-linux-gnu' doesn't exist`) — pre-existing, out of scope (no Linux sidecar staged; that's `add-tauri-gui` task 2.2). Because the script correctly propagates that failure, `build.ps1` now exits non-zero / throws even though the Windows artifact it actually produces is fine — a deliberate, accurate signal, not a regression (the original script never checked its `docker run` exit code at all, so this same gap was previously silent).

  Verification also found and fixed a real bug in this task's own script: the optional second `docker cp` (for a Linux bundle that isn't produced) was redirecting stderr with `2>$null`, which under `$ErrorActionPreference = "Stop"` turns a native command's non-zero exit into a terminating PowerShell error and aborted the whole script even after the Windows artifact had already succeeded. Fixed by not redirecting that command's stderr at all (a non-redirected native failure only sets `$LASTEXITCODE`, it doesn't throw).

- [x] 3.2 Record the new wall-clock build time against the previous ~40-50 minute baseline

  Measured: **14.9 minutes** total (`docker build` + both `cargo tauri build` legs + copy-out), vs. the ~40-50 minute baseline from the old NTFS-bind-mounted build earlier in this session — roughly **3x faster**. The `cargo` compile itself dropped to **~1m30s-1m45s** (consistent across 3 runs) for a full fresh compile of the whole dependency tree, down from a compile step that was previously dominated by per-file NTFS-bridge latency. The remainder of the 14.9 minutes is `makensis` packaging the ~260MB installer (still the single biggest cost, but now on native filesystem instead of the bridge) plus the native/Linux leg's compile before it fails.

  Trade-off accepted, not fixed: since `target/` is no longer bind-mounted, cargo's incremental-build cache no longer persists between separate `docker run` invocations — each run compiles fresh. Not worth added complexity (e.g. a `target/`-backing volume) given a fresh compile is only ~1.5-2 minutes.

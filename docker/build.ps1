# Builds the Tauri Windows (GNU/mingw cross-compile, portable folder) and
# Linux (native, AppImage) artifacts inside Docker
# (docker/tauri-build.Dockerfile), working around this machine's
# execution-policy block on native Rust toolchain binaries. No installer
# bundling as of openspec/changes/remove-installer-packaging -- each
# platform ships one no-install artifact.
#
# The source is baked into the image (COPY . /app in the Dockerfile) and
# built entirely on the container's own native filesystem -- see
# openspec/changes/fix-docker-build-filesystem/design.md. Bind-mounting
# the Windows checkout (and cargo's target/ dir) into the container was
# the dominant cost of a build, not actual compilation/packaging work.
# Only the finished artifact(s) are copied back to the host afterward.
#
# Run from the repo root: .\docker\build.ps1
$ErrorActionPreference = "Stop"

docker build -t transcriber-tauri-build -f docker/tauri-build.Dockerfile .
if ($LASTEXITCODE -ne 0) { throw "docker build failed" }

$containerName = "transcriber-tauri-build-run"
docker rm -f $containerName *>$null

try {
    docker run --name $containerName `
        -v "transcriber-cargo-registry:/usr/local/cargo/registry" `
        -w /app/src-tauri `
        transcriber-tauri-build `
        bash -c "cargo tauri build --target x86_64-pc-windows-gnu && cargo tauri build"
    $buildExitCode = $LASTEXITCODE

    # Copy back whichever output the build produced, even if the chained
    # native (Linux) build failed after the Windows one already succeeded.
    # The Windows leg has no matching bundle.targets entry (design.md
    # Decision 4), so it only ever produces the raw release/ dir, not a
    # bundle/ subdirectory -- that raw dir is exactly what
    # build_portable.py's Windows path assembles from.
    foreach ($dir in @(
        "src-tauri/target/x86_64-pc-windows-gnu/release",
        "src-tauri/target/release/bundle/appimage"
    )) {
        # Best-effort: a leg that failed before producing output makes
        # `docker cp` itself a non-zero-exit native call -- under this
        # script's $ErrorActionPreference = "Stop" that becomes a
        # terminating error, so it's caught and swallowed rather than
        # aborting the (already-succeeded) other leg's result.
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        try {
            docker cp "${containerName}:/app/$dir/." $dir
            if ($LASTEXITCODE -eq 0) { Write-Host "Copied $dir" }
        } catch {
            Write-Host "Skipped $dir (not produced by this build)"
        }
    }

    if ($buildExitCode -ne 0) { throw "cargo tauri build failed (exit $buildExitCode)" }

    # Windows artifact: assemble the portable zip from the raw release dir
    # just copied back (this script runs on the Windows host).
    python build_portable.py --target x86_64-pc-windows-gnu

    # Linux artifact: no assembly needed, just place it alongside the
    # Windows zip (build_portable.py's own Linux path only runs when
    # invoked with platform.system() == "Linux", i.e. from inside the
    # container or a native Linux CI runner -- not from this Windows host).
    $appImage = Get-ChildItem "src-tauri/target/release/bundle/appimage/*.AppImage" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($appImage) {
        New-Item -ItemType Directory -Force -Path "dist/portable" | Out-Null
        Copy-Item $appImage.FullName -Destination "dist/portable" -Force
        Write-Host "Portable artifact assembled at: dist/portable/$($appImage.Name)"
    }
}
finally {
    docker rm -f $containerName *>$null
}

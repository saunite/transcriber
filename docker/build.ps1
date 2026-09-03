# Builds the Tauri Windows (GNU/mingw cross-compile) and Linux installers
# inside Docker (docker/tauri-build.Dockerfile), working around this
# machine's execution-policy block on native Rust toolchain binaries.
#
# The source is baked into the image (COPY . /app in the Dockerfile) and
# built entirely on the container's own native filesystem -- see
# openspec/changes/fix-docker-build-filesystem/design.md. Bind-mounting
# the Windows checkout (and cargo's target/ dir) into the container was
# the dominant cost of a build, not actual compilation/packaging work.
# Only the finished installer bundle(s) are copied back to the host
# afterward.
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

    # Copy back whichever bundle director(y/ies) the build produced, even
    # if the chained native (Linux) build failed after the Windows one
    # already succeeded.
    foreach ($bundleDir in @(
        "src-tauri/target/x86_64-pc-windows-gnu/release/bundle",
        "src-tauri/target/release/bundle"
    )) {
        # Best-effort: the native (Linux) leg may not have produced a
        # bundle at all (e.g. it fails before bundling), which makes
        # `docker cp` itself a non-zero-exit native call -- under this
        # script's $ErrorActionPreference = "Stop" that becomes a
        # terminating error, so it's caught and swallowed rather than
        # aborting the (already-succeeded) Windows leg's result.
        New-Item -ItemType Directory -Force -Path $bundleDir | Out-Null
        try {
            docker cp "${containerName}:/app/$bundleDir/." $bundleDir
            if ($LASTEXITCODE -eq 0) { Write-Host "Copied $bundleDir" }
        } catch {
            Write-Host "Skipped $bundleDir (not produced by this build)"
        }
    }

    if ($buildExitCode -ne 0) { throw "cargo tauri build failed (exit $buildExitCode)" }
}
finally {
    docker rm -f $containerName *>$null
}

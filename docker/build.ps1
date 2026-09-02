# Builds the Tauri Windows (GNU/mingw cross-compile) and Linux installers
# inside Docker (docker/tauri-build.Dockerfile), working around this
# machine's execution-policy block on native Rust toolchain binaries.
# Run from the repo root: .\docker\build.ps1
$ErrorActionPreference = "Stop"

docker build -t transcriber-tauri-build -f docker/tauri-build.Dockerfile .
if ($LASTEXITCODE -ne 0) { throw "docker build failed" }

docker run --rm `
    -v "${PWD}:/app" `
    -v "transcriber-cargo-registry:/usr/local/cargo/registry" `
    -w /app/src-tauri `
    transcriber-tauri-build `
    bash -c "cargo tauri build --target x86_64-pc-windows-gnu && cargo tauri build"

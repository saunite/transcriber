## Context

See proposal.md - Why. `01`'s design covers the workflow shape, the smoke test, and the CLI archive; this design covers only what is Windows-specific.

- **The local Windows build** cross-compiles the shell from WSL with the `x86_64-pc-windows-gnu` target and mingw-w64, and freezes the sidecar through a Windows Python venv reached from WSL (`wsl-windows-build`). That combination is verified on real hardware (`05`).
- **GNU plus NSIS has worked before.** `add-tauri-gui` task 7.1 built a 259 MB NSIS installer for `x86_64-pc-windows-gnu` in the former Docker build, from a Linux host.
- **On the GNU target, `WebView2Loader.dll` ships as a separate file** next to the exe. `build_portable.py` already copies it when present.

## Goals / Non-Goals

**Goals:**
- Build the Rust shell entirely with open-source tools, as the user prefers.
- An installer that never asks for admin rights.

**Non-Goals:**
- Code signing. SmartScreen warns on the installer exactly as it already does on the portable exe.
- An MSI package.
- Replacing the local WSL build.

## Decisions

### 1. Native Windows runner, GNU target, and a GNU host toolchain

Setting only `--target x86_64-pc-windows-gnu` isn't enough on a Windows runner. Its default Rust toolchain is `stable-x86_64-pc-windows-msvc`, and build scripts and proc-macros are compiled for the host, so Microsoft's `link.exe` would still link them. Running `rustup default stable-x86_64-pc-windows-gnu` makes the host GNU too, so the whole Rust build uses mingw-w64.

- **mingw-w64** comes from the runner's preinstalled MSYS2/mingw, or from `msys2/setup-msys2` with `mingw-w64-x86_64-gcc` if that isn't on `PATH`. `src-tauri/.cargo/config.toml` expects a linker named `x86_64-w64-mingw32-gcc`, and MSYS2's mingw64 package provides that name. Verify it; don't assume.
- **The sidecar remains python.org CPython plus MSVC-built wheels.** There's no open-toolchain alternative: ctranslate2 and onnxruntime publish no mingw wheels. This is the one real gap, and it's upstream.
- **Rejected: MSVC target.** It's a closed toolchain, and a build configuration this project has never tested.
- **Fallback, not planned:** cross-compile the shell and NSIS on an Ubuntu job, exactly like the local WSL build, and freeze the sidecar in a separate Windows job, passing the frozen file between jobs. This is proven to work (Docker era), but it doubles the moving parts. Use it only if this decision's single-job approach fails in a way that can't be fixed quickly.

### 2. NSIS with `installMode: "currentUser"`

The installer puts the app under `%LOCALAPPDATA%` and adds a per-user Start Menu entry and uninstaller, with no UAC prompt. Tauri downloads NSIS itself, and NSIS is open source (zlib license). `webviewInstallMode` stays at its default: the WebView2 bootstrapper only runs when the runtime is missing, and Windows 10 and 11 already have it. MSI was rejected because it needs WiX and defaults to a per-machine install.

### 3. The installer must carry `WebView2Loader.dll`

With the GNU target, the exe needs this DLL next to it. Check on the first build whether Tauri's NSIS bundling includes it for GNU targets. If it doesn't, add it through `bundle.resources` for Windows builds only.

### 4. Batch launcher fallback, printed from the same variable

`if exist "%~dp0transcriber.exe"` sets the runner to the bundled exe; otherwise it keeps `python transcriber.py`. The existing `CMD` variable is then built from it, so the printed command and the executed command stay the same value. `transcribe_file.bat` gets the same fallback in place of its hard-coded `.venv\Scripts\python.exe transcriber.py`.

### 5. Clean-machine checks stay manual

A GitHub Windows runner is clean but runs as an administrator with no desktop, so it can't prove that no UAC prompt appears. The non-admin install check and the portable clean-machine check from `05` task 2.4 need a real standard-user account on a machine that has never had the app. Windows Sandbox isn't available on the managed development host (`05` task 2.4), so this needs another PC or a cloud VM.

## Risks / Trade-offs

- **[Risk]** mingw isn't on `PATH` under the expected name → add `msys2/setup-msys2` and put `C:\msys64\mingw64\bin` on `PATH`.
- **[Risk]** A dependency's build script assumes MSVC when the host is GNU → it would show up as a build failure on the first run. The local WSL build already compiles every crate for the GNU target, so only host-side build scripts are at risk.
- **[Risk]** A clean machine may not be available soon → the clean-machine tasks stay open, as `05`'s did. The installer is still usable in the meantime.
- **[Trade-off]** The mingw in CI (MSYS2's) differs from the local one (Ubuntu's package). Both use the same target triple and the same DLL layout.

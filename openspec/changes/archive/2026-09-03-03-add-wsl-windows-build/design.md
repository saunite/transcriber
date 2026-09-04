## Context

See proposal.md - Why. This change is the Windows counterpart to `02-add-wsl-linux-build` and depends on it for the base toolchain (`rustup`, `cargo install tauri-cli`, `CARGO_TARGET_DIR`). Today the only proven Windows build path is `docker/build.ps1`'s `cargo tauri build --target x86_64-pc-windows-gnu` leg, run from a Windows host driving the container.

## Goals / Non-Goals

**Goals:**
- Produce the same `Transcriber.zip` (mingw-built `transcriber-gui.exe` + frozen `transcriber-sidecar.exe` + model) from a WSL shell, with no container and no manual step on a separate Windows host.
- Fail loudly and specifically when the interop step's prerequisite (a reachable Windows Python) is absent, rather than silently building a broken or stale artifact.

**Non-Goals:**
- Linux build (`02`).
- Removing the container or CI (`04`).
- Signing or notarizing the Windows binary (unrelated, not previously done either).
- Changing what `build_sidecar.py` or `fetch_sidecar_resources.py` do — both already work correctly; this change only changes *what process invokes them*.

## Decisions

**Interop via WSL's native ability to execute Windows binaries**, not a separate CI leg or manual step. WSL2 executes `.exe` files transparently, and the repo's existing `.venv/Scripts/python.exe` — confirmed during exploration to be a genuine Windows-targeted venv with every sidecar dependency (`faster_whisper`, `PyInstaller`, `pyaudiowpatch`, `sounddevice`, `av`) already installed — is reachable at the same path from both sides, since the repo checkout is shared. Alternative considered: a lightweight Windows CI/build VM — rejected as exactly the kind of infrastructure this migration is trying to remove.

**Probe for the specific venv interpreter, not a generic `python.exe` on `PATH`.** `platform.system()` inside a WSL process reports `"Linux"`, never `"Windows"` — no OS-sniff answers "is a Windows Python reachable from here." The first attempt at this used `shutil.which("python.exe")` — wrong, discovered during implementation: on this machine it resolves to the Windows Store's stub launcher (`.../WindowsApps/python.exe`, Python 3.13), a real, executable interpreter with none of the sidecar dependencies installed. A `which`-based guard would pass, then the freeze would fail confusingly inside `build_sidecar.py` with `ModuleNotFoundError`, defeating the guard's purpose (fail clearly, not confusingly). The correct check is existence + executability of the specific repo-relative path this change actually invokes — `<repo>/.venv/Scripts/python.exe` — since that is the only interpreter guaranteed to have the right dependencies. `PATH` lookups answer "is *some* Windows Python reachable," not "is *the* Windows Python with the sidecar deps reachable"; only the second question matters here.

**Fix `build_portable.py`'s dispatch to key off `--target`, not the running interpreter.** `main()` currently does `platform.system()` to choose `build_windows`/`build_linux`/`build_macos`. Run from WSL with `--target x86_64-pc-windows-gnu`, that reports `"Linux"` and silently takes the wrong branch. Since every call site already passes `--target` explicitly (CI, the old `build.ps1`, and this change's own build steps), branching on the triple's substring (`"windows"`/`"linux"`/`"darwin"` in `target`) when a target is given — falling back to `platform.system()` only when none is passed, preserving today's plain `cargo tauri build` (no target) behavior — is a strict improvement with no behavior change for existing callers.

**No interop needed for `build_portable.py` itself.** `build_windows()` is pure `shutil`/`zipfile` file operations — no Windows-only API. Once dispatch is fixed, it runs correctly under WSL's own Python; only the PyInstaller freeze genuinely requires a Windows interpreter.

## Risks / Trade-offs

- [The Windows venv (`.venv/Scripts/python.exe`) is a manually-managed local artifact, not reproducible from a lockfile in this change's scope] → Mitigation: out of scope here (documented as a possible future improvement, not blocking); the venv already exists and works, verified during exploration.
- [WSL's `/mnt/c/...` DrvFs path being used for the interop call is slow for the PyInstaller freeze itself] → Mitigation: accepted — this is a rare, one-shot freeze (not an incremental-compile hot path like `cargo`), so the `CARGO_TARGET_DIR` fix in `02` (which optimizes the frequent, incremental cargo I/O) matters far more than this occasional, unavoidable cost.
- [`build_portable.py`'s dispatch fix changes behavior for any caller relying on the old `platform.system()`-only logic] → Mitigation: every existing caller already passes `--target` explicitly (confirmed by grep across `docker/build.ps1` and `.github/workflows/build-gui.yml`), so the fallback path is unreachable in practice today; the change only fixes the currently-broken WSL case.

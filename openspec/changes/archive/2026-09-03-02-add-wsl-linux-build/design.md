## Context

See proposal.md - Why. Today the only proven Linux build path is inside `docker/tauri-build.Dockerfile` via `docker/build.ps1`'s native (no `--target`) leg. This change reproduces that leg directly in WSL, as the first of two native-build changes (`03-add-wsl-windows-build` follows) that together let `04-remove-ci-and-container-builds` delete the container and CI without losing either platform's build.

## Goals / Non-Goals

**Goals:**
- Native `cargo tauri build` from WSL produces the same `.AppImage` the container currently does.
- Cargo's working-set I/O stays off any Windows-mounted (DrvFs) path, matching the container's own filesystem requirement (`openspec/specs/docker-build/spec.md`).

**Non-Goals:**
- Windows cross-compilation (`03`).
- Removing the container or CI (`04`) — that happens only after both native paths are proven.
- Reinstalling this toolchain automatically (no orchestration script beyond documenting/running the commands) — a one-time `apt install` + `rustup`/`cargo install` is a setup step, not a repeated build step.

## Decisions

**Reuse the CI `ubuntu-latest` package list verbatim**, rather than re-deriving it. `.github/workflows/build-gui.yml`'s Linux-deps step and `docker/tauri-build.Dockerfile` are both already-proven sources for "what does a native Ubuntu/Debian Tauri Linux build need" — no reason to guess a smaller list.

**Drop Node.js from the toolchain.** CI's `setup-node@v4` step installs Node, but `tauri.conf.json`'s `build.frontendDist` points at static `../src` with no `beforeBuildCommand`/`beforeDevCommand` — confirmed by grep, no npm/node reference anywhere in `src-tauri/`. The frontend is plain HTML/JS/CSS; Node was never load-bearing.

**`CARGO_TARGET_DIR` env var, not a symlink.** Both relocate cargo's `target/` to ext4 with zero change to `build_portable.py`'s literal path structure, but the env var needs no untracked filesystem object in the repo tree, and `_release_dir()` needs a small edit regardless (see below) — so the marginal cost of reading the env var there is near zero. Alternative considered: a symlink at `src-tauri/target` pointing into ext4 — rejected only because it's strictly more setup for the same result once `_release_dir()` is being touched anyway.

**Fix `_release_dir()` to honor `CARGO_TARGET_DIR`.** Currently hardcodes `REPO_ROOT / "src-tauri" / "target"`. Cargo itself already respects the env var for where it writes; `build_portable.py` must look in the same place: read `os.environ.get("CARGO_TARGET_DIR")` and fall back to the current hardcoded path when unset (so the script still works for a contributor who hasn't set it).

**Also set `build.target-dir` in `~/.cargo/config.toml` (machine-local, not repo-tracked), not just the env var.** Discovered during implementation: an exported `CARGO_TARGET_DIR` only takes effect if the shell that runs `cargo` actually has it set — easy to forget in a fresh shell, with no error, just a silent fall-through to the slow path. The user-level cargo config applies regardless of shell state and still yields to an explicit env var if one is set, so it's a strict improvement with no downside.

**Check out the repo itself on WSL's native filesystem, not `/mnt/c/...`.** Discovered during implementation, via a real WSL notification about cargo accessing NTFS mid-build: `CARGO_TARGET_DIR` only relocates cargo's *output*. The *source* — `Cargo.toml`, every `src-tauri/src/*.rs`, `tauri.conf.json` — and Tauri's generated `src-tauri/gen/` output still live wherever the checkout is, and get read/written every build regardless of `CARGO_TARGET_DIR`. Moved the checkout from `/mnt/c/Users/.../transcriber` to `~/repos/transcriber` (ext4); verified afterward that the Windows Python interop (`.venv/Scripts/python.exe`, needed for `03-add-wsl-windows-build`'s sidecar freeze) still works, reached via WSL's `\\wsl.localhost\...` path — the cost of that crossing lands on the one-shot freeze, not the frequent incremental build, so it doesn't reopen the problem this change fixes.

## Risks / Trade-offs

- [Toolchain packages drift from what CI/Docker used, causing an "works in container, not in WSL" gap] → Mitigation: the package list is copied from the CI job, a source already proven working; any future divergence is caught by the AppImage smoke-test in tasks.md.
- [A contributor forgets to set `CARGO_TARGET_DIR` and gets a slow build] → Mitigated by the persistent `~/.cargo/config.toml` decision above — no per-shell state to forget.
- [A contributor checks the repo out under `/mnt/c/...` anyway] → Mitigation: called out explicitly in the README's WSL build section, with the reason (not just "do this," but why `CARGO_TARGET_DIR` alone isn't enough) so it isn't silently skipped.

## Context

See proposal.md - Why for the step timings (run 34656473927). The three targets as they stand in `.github/workflows/release.yml`:

- `actions/setup-python@v6` is used with only `python-version`, so no dependency caching.
- The freeze step creates `.venv` and runs `pip install -r requirements-linux.txt pyinstaller` from scratch each run.
- The build step runs `npx @tauri-apps/cli build` with no cargo cache, so `src-tauri/target` starts empty.
- The install-check step loops over `debian:stable`, `ubuntu:24.04`, `fedora:latest`, `opensuse/leap:latest` and `opensuse/tumbleweed` sequentially under `set -e`, with a `::group::` per distro.

## Goals / Non-Goals

**Goals:**
- Remove repeated download and compile work, and stop waiting on five independent checks in series.
- Keep every check that runs today, with failures still attributable to a specific distro.

**Non-Goals:**
- The rpm payload compression (its own change, `switch-rpm-compression-to-zstd`).
- Caching the bundled model (`fetch_sidecar_resources.py`): it's one 141 MB download from Hugging Face inside the 1m55s step, and caching it trades a network fetch for a cache fetch of the same size.
- Building fewer bundle types on tagged runs, or skipping the AppImage.
- Self-hosted or larger runners.

## Decisions

### 1. `Swatinem/rust-cache` for the cargo build

Added before the build step, with no key configuration: the action already keys on `Cargo.lock` plus the compiler version, saves `~/.cargo` and `src-tauri/target`, and prunes intermediates it knows are unnecessary. `workspaces: src-tauri` points it at this project's layout.

The honest limits: a `Cargo.lock` change invalidates it, GitHub evicts caches unused for 7 days, and this repo releases rarely — so a cold run remains common. The saving is also smaller than the 2m30s compile suggests, because restoring a `target/` archive for a Tauri app is itself hundreds of MB of I/O. Treat "compile 2m30s → ~40s on a hit" as the optimistic end.

**Rejected: `sccache` or a self-managed `actions/cache` of `~/.cargo` alone.** More configuration, and `rust-cache` exists for exactly this.

### 2. `cache: pip` on `setup-python`

One line on the existing step, keyed on `requirements-linux.txt`. It caches pip's HTTP/wheel cache, so the wheels are fetched from GitHub's cache instead of PyPI. PyInstaller's freeze work itself is unaffected, so the step drops to roughly a minute rather than vanishing.

`setup-python`'s cache expects the requirements file path; the workflow's `requirements-linux.txt` is at the repo root, which is the action's default lookup, so no extra path config is needed — task 1.2 confirms that from the run log rather than assuming.

### 3. The five install checks run concurrently, in the same job

Each check is `docker run` against a package already on disk in `out/`. They share nothing, so they can run at once; the step becomes a small parallel fan-out that waits for all of them and fails if any failed. The `::group::` markers move to per-distro log files that are printed after each finishes, so concurrent output doesn't interleave into noise.

**Rejected: a separate matrix job** (my first suggestion when exploring). A matrix job cannot see `out/`, so the `.deb` and `.rpm` (312 MB each) would have to be uploaded as artifacts and downloaded again by five jobs — roughly 1.5 GB of transfer to save 2m30s, plus the artifact upload on the critical path. Parallelising inside the job gets the same wall-clock win with none of that.

**Failure attribution matters more than brevity here.** The step's value is telling you *which* distro's package manager refused, which is exactly how the earlier Fedora wildcard bug was found. So each check writes its own log and exit code, and the step prints every failed distro's log before exiting non-zero.

## Risks / Trade-offs

- **[Risk]** Five concurrent `docker run`s on a 4 vCPU runner contend for CPU and network, so the wall time won't be a clean 1/5 of 3m27s → task 1.3 records the real figure. Even a 2× improvement is worth the change.
- **[Risk]** A stale Rust cache produces a confusing build failure → `rust-cache` keys on lockfile and toolchain, and the fallback is deleting the cache entry in the Actions UI. Noted here so the symptom is recognisable.
- **[Trade-off]** Concurrent logs are harder to read than sequential ones. Mitigated by per-distro log files printed on completion, and only failures printed in full.
- **[Trade-off]** Caches make runs less hermetic: a green run no longer proves a from-scratch build works. The tagged release path still compiles the app itself every time, and a cache miss (which will happen regularly here) is a full cold build.

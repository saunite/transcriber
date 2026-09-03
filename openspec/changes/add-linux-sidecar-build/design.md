## Context

`.github/workflows/build-gui.yml` already has an `ubuntu-latest` matrix entry that runs `build_sidecar.py` (PyInstaller `--onefile`), stages the frozen binary into `src-tauri/binaries/`, and builds the Linux Tauri bundle. It was written without ever being run — the file's own header says `UNVERIFIED`. The equivalent Windows path (`add-tauri-gui` tasks 2.1/2.4) needed two real fixes only discoverable by actually running the frozen binary: a `UnicodeEncodeError` on piped stdout, and a missing PyInstaller `--add-data` for faster-whisper's bundled VAD ONNX model. There is every reason to expect Linux has its own undiscovered issues (different libc, different default stdout encoding behavior, WSL/PyAV shared-library quirks) that only show up by running it for real.

This machine has Docker (already used for the Windows cross-compile in `fix-docker-build-filesystem`) but PyInstaller does not cross-compile — a Linux freeze must run on actual Linux, whether that's this machine's Docker (a Linux container is a legitimate native-Linux host for this purpose, unlike the Windows cross-compile case) or GitHub's `ubuntu-latest` runner.

## Goals / Non-Goals

**Goals:**
- Get the Linux sidecar freeze to actually run once, for real, and fix whatever it surfaces.
- Smoke-test the frozen binary standalone before trusting it's wired into the Tauri bundle correctly (mirrors `add-tauri-gui` task 2.4).
- Remove the `UNVERIFIED` claim from `build-gui.yml` once it's backed by a real, passing run.

**Non-Goals:**
- Not building a full Linux Tauri bundle/AppImage end-to-end here — that's `remove-installer-packaging`'s territory (its Linux path already assumes a working frozen sidecar; this change is what makes that assumption true). This change stops at: the frozen sidecar binary works standalone.
- Not adding macOS — that's `remove-installer-packaging` task 3.4.
- Not switching PyInstaller modes (`--onefile` vs `--onedir`) — out of scope, same as it was for Windows.

## Decisions

**Freeze and smoke-test locally via Docker first, then confirm via the actual GitHub Actions run.**
A plain `ubuntu` Docker container on this machine can run `build_sidecar.py` and the smoke tests (`--list-devices-json`, `--file`) without needing a GitHub Actions run in the loop for every iteration — much faster feedback than push-and-wait, and this machine already has Docker set up and working (`fix-docker-build-filesystem`). The actual `ubuntu-latest` GitHub Actions job is still triggered and confirmed passing at the end, since that's the real artifact-producing path and a local container isn't guaranteed identical (different base image, different libc version).
- Alternative considered: only trigger the CI workflow and iterate by pushing fixes. Rejected as needlessly slow for what will likely be a couple of rounds of "run, hit an error, fix, re-run" — the same pattern the Windows freeze went through.

**`--list-devices-json` on Linux will legitimately report zero devices in a Docker container** (no real audio hardware, no PulseAudio/ALSA device exposed into the container) — that's expected, not a bug. The meaningful smoke test on Linux is `--file` transcription of a sample clip, matching what actually gets exercised in the Tauri bundle's file-transcription flow. Live capture on Linux is out of scope entirely (no live-capture UI path exists for Linux in `desktop-gui` today).

## Risks / Trade-offs

- [A Docker-container freeze might behave subtly differently from the actual `ubuntu-latest` GitHub runner (different glibc version, different base image)] → Mitigation is already built into the plan: the GitHub Actions run is still the final confirmation, not skipped in favor of the local one.
- [The first real run may surface a Linux-specific bug whose fix isn't obvious in advance] → Same as the Windows precedent: fix it when found, verify by re-running, don't guess at fixes ahead of evidence.

## Migration Plan

1. Run `build_sidecar.py` inside a Linux Docker container; fix whatever it surfaces.
2. Smoke-test the resulting binary (`--list-devices-json`, `--file` on a sample clip) standalone in that same container.
3. Trigger `build-gui.yml` for real (`workflow_dispatch`) and confirm the `ubuntu-latest` job passes end-to-end.
4. Remove the `UNVERIFIED` header comment from `build-gui.yml` once (3) passes.

No rollback complexity: this only touches the Linux CI leg and, if needed, small cross-platform fixes in `transcriber.py`/`build_sidecar.py` — nothing Windows-specific is at risk.

## Open Questions

- None — this follows the exact precedent `add-tauri-gui` already set for Windows (freeze → smoke-test → fix what's found → confirm).

## 1. Workflow changes

- [x] 1.1 Add `Swatinem/rust-cache@v2` with `workspaces: src-tauri` before the "Build GUI packages" step (design.md Decision 1). Verify on the next two runs: the first logs a cache miss and saves a cache, the second logs a hit and its cargo compile is faster than the 2m30s baseline. Record both numbers here.
- [x] 1.2 Add `cache: pip` to the existing `actions/setup-python@v6` step (design.md Decision 2). Verify in the run log that the step reports a cache hit on the second run, and that "Freeze sidecar and stage resources" drops below its 1m55s baseline.
- [x] 1.3 Rewrite the "Install checks on target distros" step to run its five container checks concurrently, each writing a per-distro log and exit code, printing every failed distro's log, and exiting non-zero if any failed (design.md Decision 3). Verify two things: on a normal run all five still pass and the step's duration is below the 3m27s baseline (record it); and on a scratch run with one dependency name deliberately broken, the step fails and names the distro that refused the package.


  **Implemented and locally verified 2026-09-11; the timing halves need the next tagged run.**

  - **1.1** `Swatinem/rust-cache@v2` with `workspaces: src-tauri` sits immediately before "Build GUI packages" (confirmed by parsing the workflow's step list). A cache *hit* cannot be shown in one run: the first run populates the cache, so the ~40s compile figure is only measurable on the run after that. Recorded as pending rather than claimed.
  - **1.2** `cache: pip` is on the existing `setup-python` step, with `cache-dependency-path: requirements-linux.txt`. **Deviation from design.md Decision 2, deliberate:** the design said no path config was needed, but the action's default pip lookup is `**/requirements.txt`, which in this repo is the *Windows* requirements file — the cache would have keyed on the wrong dependencies. Like 1.1, the hit only shows from the second run onwards.
  - **1.3** The five checks now run concurrently, each writing `check-<distro>.log`, with `wait` per child, `::error::` plus the full log for failures, and a non-zero exit if any failed. Verified without CI by extracting the step's script and running it against a stub `docker`: with one image rigged to fail, the step exited 1, finished in 1s (concurrent; serial would be ~5s), invoked all five images, and annotated only `opensuse/leap:latest` while reporting the other four as passed. An earlier accidental run against the real (absent) docker daemon also confirmed the all-fail path names every distro. `yamllint` passes and the extracted script passes `bash -n`.

## 2. Confirm nothing was lost

- [x] 2.1 On the next tagged run, check that the release still receives the same five assets and that all five distro checks appear in the log, so the speed-ups didn't quietly drop a check. Compare the total job duration against the ~32m baseline of run 34656473927 (and against whatever `switch-rpm-compression-to-zstd` leaves it at, if that landed first) and record the figure.

  **Verified 2026-09-12** (run 34672668438, tag `v0.1.0` on `77df1da`, which carried both this change and `switch-rpm-compression-to-zstd`).

  Nothing was lost: the draft received the same five assets (`transcriber-0.1.0-1.x86_64.rpm`, `transcriber_0.1.0_amd64.deb`, `transcriber_0.1.0_amd64.AppImage`, `transcriber-cli_0.1.0_linux-x64.tar.gz`, `SOURCE-PROVENANCE.txt`), and all five distro checks appear in the log as `<distro> passed`, with the openSUSE ones showing `Installing: transcriber-0.1.0-1.x86_64 [...done]`.

  | Step | Baseline (34656473927) | This run |
  |---|---|---|
  | Install checks (5 distros) | 3m27s | **1m21s** |
  | Cargo compile | 2m30s | 3m09s (cache miss, cold) |
  | Freeze sidecar | 1m55s | 2m10s (cache miss, wheels downloaded) |
  | Build GUI packages (whole step) | 25m30s | 15m50s |
  | Linux job total | ~32m | **~20m30s** |

  **The caches are populated but unproven, as predicted.** pip logged `pip cache is not found` and then `Cache saved with the key: setup-python-Linux-x64-22.04-Ubuntu-python-3.14.7-pip-…`; rust-cache ran with `workspaces: src-tauri` and saved in its post step. Both compile and freeze came in slightly *above* baseline this run, which is the expected cost of a cold cache plus normal runner variance. Tasks 1.1 and 1.2's hit figures can only be measured on the next tagged run — carry them forward rather than treating this run as their verification.

  Most of the 11.5 minutes saved here came from `switch-rpm-compression-to-zstd` (rpm bundling 21m14s → 10m11s); this change contributed the install-check saving (~2m) and set up the caches for later runs.

## 1. Workflow changes

- [ ] 1.1 Add `Swatinem/rust-cache@v2` with `workspaces: src-tauri` before the "Build GUI packages" step (design.md Decision 1). Verify on the next two runs: the first logs a cache miss and saves a cache, the second logs a hit and its cargo compile is faster than the 2m30s baseline. Record both numbers here.
- [ ] 1.2 Add `cache: pip` to the existing `actions/setup-python@v6` step (design.md Decision 2). Verify in the run log that the step reports a cache hit on the second run, and that "Freeze sidecar and stage resources" drops below its 1m55s baseline.
- [ ] 1.3 Rewrite the "Install checks on target distros" step to run its five container checks concurrently, each writing a per-distro log and exit code, printing every failed distro's log, and exiting non-zero if any failed (design.md Decision 3). Verify two things: on a normal run all five still pass and the step's duration is below the 3m27s baseline (record it); and on a scratch run with one dependency name deliberately broken, the step fails and names the distro that refused the package.

## 2. Confirm nothing was lost

- [ ] 2.1 On the next tagged run, check that the release still receives the same five assets and that all five distro checks appear in the log, so the speed-ups didn't quietly drop a check. Compare the total job duration against the ~32m baseline of run 34656473927 (and against whatever `switch-rpm-compression-to-zstd` leaves it at, if that landed first) and record the figure.

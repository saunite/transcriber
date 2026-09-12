## Why

After `switch-rpm-compression-to-zstd` removes the dominant cost, the release workflow's remaining time is mostly work the runner repeats every time. Measured from run 34656473927:

```
system packages (apt)              42s
freeze sidecar (pip + PyInstaller) 1m55s   <- pip downloads most of it
build GUI packages                25m30s   <- of which cargo compile 2m30s
install checks on 5 distros        3m27s   <- five sequential docker pulls + installs
upload to draft                     24s
```

Three of those are avoidable:

- **Cargo recompiles ~450 dependency crates on every run** (2m30s), though `Cargo.lock` rarely changes.
- **pip re-downloads the sidecar's wheels every run** (ctranslate2, onnxruntime, av and friends), which is most of the 1m55s freeze step.
- **The five distro install checks run one after another** (3m27s), each pulling its image and installing, even though they're independent.

## What Changes

- **Cache the Rust build** with `Swatinem/rust-cache`, keyed on `Cargo.lock`, so only this project's own crate recompiles on a cache hit.
- **Cache pip downloads** via `actions/setup-python`'s `cache: pip`, keyed on `requirements-linux.txt`.
- **Run the five container install checks concurrently** inside the existing job, instead of sequentially, keeping per-distro failure reporting.

Expected: roughly 2m45s from the caches (on a hit) and ~2m30s of wall time from the parallel checks — about 5 minutes off a run that, with zstd, should be ~17m.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
(none — nothing about the artifacts, their contents, or their verification changes. `01-add-release-pipeline`'s "Linux release artifacts" requirement still demands the `.deb` install on Debian and Ubuntu and the `.rpm` on Fedora, Leap and Tumbleweed; this change only stops running those checks in single file.)

This change sets `skip_specs: true` in `.openspec.yaml`.

## Impact

- **Changed**: `.github/workflows/release.yml` only.
- **Unchanged**: every artifact, every check performed, and the draft-release flow.
- **Depends on nothing**, but it's worth applying after `switch-rpm-compression-to-zstd` so the measurements aren't hidden behind the 21-minute rpm step.
- **Honest caveat**: caches only pay off on a hit. `Cargo.lock` changes and GitHub's 7-day eviction both cause misses, and releases are infrequent, so some runs will see no benefit at all. See design.md.

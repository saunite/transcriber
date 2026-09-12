## Why

The release workflow takes ~32 minutes, and bundling the `.rpm` alone accounts for 21m14s of it — 66% of the whole Linux job. Measured from run 34656473927:

```
Build GUI packages step: 25m30s
  npx CLI fetch + version check      11s
  cargo compile (release)         2m30s
  AppImage (linuxdeploy)          1m23s
  .deb                               8s   <- same ~293 MB payload
  .rpm                           21m14s   <- 66% of the job
```

The `.deb` packs the identical payload in 8 seconds, so this is not the payload's size. A throwaway harness built the same package with the `rpm` crate three ways, on the real 293 MB payload (the frozen sidecar plus the bundled model):

| Payload compression | Time | Output | Peak RAM |
|---|---|---|---|
| `None` | 4.4s | 293.2 MB | 725 MB |
| `Zstd` level 3 | 12m25s | 278.0 MB | 715 MB |
| `Gzip` level 6 (Tauri's default) | 45m24s | 278.2 MB | 712 MB |

So the cost is the compressor path inside the `rpm` crate, not memory (flat ~715 MB) and not the crate's per-file copying (`None` finishes in seconds). Tauri's own source comment anticipates this, noting `Gzip(6)` was chosen to match the `.deb` and that it plans to default to Zstd in v3.

Switching to zstd level 3 is ~3.7× faster with no size cost: 278.0 MB vs 278.2 MB, a 0.2 MB difference.

## What Changes

- **`src-tauri/tauri.conf.json` sets the RPM payload compression to zstd level 3**, under `bundle.linux.rpm`:

  ```json
  "compression": { "type": "zstd", "level": 3 }
  ```

  Tauri's default is Gzip level 6 when this is unset.
- **Nothing else.** Same files in the package, same dependencies, same names, same install behavior. Only the payload's internal compression and the build time change.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
(none — no requirement describes build duration or the payload's compression format. `01-add-release-pipeline`'s "Linux release artifacts" requirement, which says the `.rpm` must install with its dependencies resolved on current Fedora, openSUSE Leap and Tumbleweed, is the guard this change must not break; its wording stays as it is.)

This change sets `skip_specs: true` in `.openspec.yaml`.

## Impact

- **Changed**: `src-tauri/tauri.conf.json` (one setting).
- **Expected effect on CI**: the rpm bundling step drops from ~21m to roughly 6m, taking the Linux job from ~32m to ~17m. Local builds benefit the same way.
- **Risk to manage**: zstd-compressed rpm payloads need RPM 4.14+ to install. Fedora and openSUSE Leap 15+/Tumbleweed have supported it for years, and the workflow's existing install checks on `fedora:latest`, `opensuse/leap:latest` and `opensuse/tumbleweed` prove it per release rather than by assumption.
- **Not pursued here**: `None` (4.4s, +15 MB) and dropping the `.rpm` target. See design.md.

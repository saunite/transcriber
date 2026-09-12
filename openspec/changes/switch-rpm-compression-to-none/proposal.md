## Why

`switch-rpm-compression-to-zstd` took the `.rpm` bundling step from 21m14s to 10m11s (run 34672668438). It is still the single largest cost in the release: the whole Linux job is ~20m30s, so bundling one package is half of it. The benchmark taken for that change also measured the next step, on the real 293 MB payload:

| Payload compression | Time | Output |
|---|---|---|
| `Gzip(6)` (Tauri's default) | 45m24s | 278.2 MB |
| `Zstd(3)` (today) | 12m25s | 278.0 MB |
| `None` | **4.4s** | 293.2 MB |

The payload is a CTranslate2 model plus a PyInstaller binary — already-compressed data. Every compressor lands at ~94.8% of the input, so the minutes buy about 5% of size. `None` is ~170× faster than zstd here and makes rpm bundling effectively free.

The user chose this trade knowingly: **~10 minutes of every release, for ~15 MB (14.5 MiB) of download.**

## What Changes

- **`src-tauri/tauri.conf.json` sets the RPM payload compression to none**, replacing `{ "type": "zstd", "level": 3 }`:

  ```json
  "compression": { "type": "none" }
  ```

- **Nothing else.** Same files, same dependencies, same package name, same install behavior. The payload is simply stored rather than compressed.

Expected: rpm bundling ~10m11s → seconds, taking the Linux job from ~20m30s to roughly 10m. The `.rpm` grows from ~297 MB to ~312 MB.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
(none — no requirement describes the payload's storage format or the build's duration. `01-add-release-pipeline`'s "Linux release artifacts" requirement, which says the `.rpm` must install with its dependencies resolved on current Fedora, openSUSE Leap and Tumbleweed, is the guard this must not break; its wording is unchanged.)

This change sets `skip_specs: true` in `.openspec.yaml`.

## Impact

- **Changed**: `src-tauri/tauri.conf.json` (one setting).
- **Download grows ~15 MB** for RPM-family users. The `.deb`, AppImage and CLI archive are untouched.
- **Risk to manage**: an uncompressed RPM payload is unusual, even though the format allows it. Whether `dnf` and `zypper` accept one is exactly what the workflow's five install checks test, per release, so the risk is measured rather than assumed. If any refuses, reverting is a one-line change back to zstd.
- **Also unchanged**: the local build path, which benefits identically.

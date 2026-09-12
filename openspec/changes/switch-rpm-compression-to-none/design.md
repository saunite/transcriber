## Context

See proposal.md - Why for the measurements, which come from the harness built during `switch-rpm-compression-to-zstd` (a throwaway Cargo project using `rpm` 0.16, the same crate `tauri-bundler` uses, run against the real `dist/linux/transcriber-sidecar` plus every file in `src-tauri/resources/model/`, timed with `/usr/bin/time -v`).

Two facts from that investigation shape this change:

- **The cost is the crate's compressor path, not the payload.** With `None`, the same crate writes the same package in 4.4 seconds, so its per-file copying, cpio framing and SHA-256 hashing are not the bottleneck. Peak memory was flat at ~715 MB across all three modes.
- **Compression achieves ~5% here.** `gzip -6` standalone compresses this payload to 94.8%; so does `zstd -3`; so does `zstd -12`. The model weights and the PyInstaller binary are already compressed.

The RPM format records its payload compressor in the header (`PAYLOADCOMPRESSOR`), and `rpm -qp --qf '%{PAYLOADCOMPRESSOR}'` reads it back — that is how zstd was confirmed in CI, and it is how `none` will be.

## Goals / Non-Goals

**Goals:**
- Make `.rpm` bundling effectively free, accepting a ~15 MB larger download.

**Non-Goals:**
- Touching the `.deb` (8s), the AppImage (1m23s) or the CLI archive.
- Reporting the `rpm` crate's slowness upstream. Still worth doing — 107 KB/s for gzip and 393 KB/s for zstd inside the crate, versus 29 MB/s and 436 MB/s standalone — but it is not this change.
- Reducing the payload itself (for example, downloading the model on first run instead of bundling it). That would contradict `desktop-gui`'s "Fully offline first run" requirement.

## Decisions

### 1. `{ "type": "none" }`, the config's own way of saying uncompressed

Tauri's `RpmCompression` enum is internally tagged and includes a `None` variant, so the config value is `{ "type": "none" }` — no level field, since there is nothing to tune. The bundler maps it to `rpm::CompressionWithLevel::None`, which stores the cpio payload verbatim.

### 2. The install checks are the compatibility test, not an assumption

An uncompressed payload is legal in the RPM format, but it is rare in practice, so the honest position is that this needs testing rather than reasoning. The workflow already installs the built `.rpm` in `fedora:latest`, `opensuse/leap:latest` and `opensuse/tumbleweed` containers and fails the leg if any refuses. That converts "should work" into "verified per release". Task 1.2 also re-checks the two RPM families explicitly, and task 1.3 installs the package on real Fedora hardware.

**If a package manager refuses**, the fallback is immediate and known-good: revert to `{ "type": "zstd", "level": 3 }`, which is verified working (run 34672668438, and a user-confirmed install/transcribe/remove cycle).

### 3. Keep the size cost visible in the README's download table

The RPM-family download becomes the largest artifact at ~312 MB, about 15 MB more than the `.deb`. The README already lists the files without sizes, so nothing needs changing there — but task 1.4 checks that the packages' relative sizes don't make any existing README statement wrong.

## Risks / Trade-offs

- **[Trade-off]** RPM users download ~15 MB more, forever, to save ~10 minutes per release build. Deliberate, and the user's explicit choice. Revisit if release frequency ever drops to the point where build minutes stop mattering.
- **[Risk]** An older `dnf`/`zypper` outside the tested distros mishandles an uncompressed payload → the tested set is exactly the distros `01` claims support for; anything older is already excluded by the glibc baseline of the `ubuntu-22.04` builder.
- **[Risk]** A future reader assumes compression was forgotten rather than chosen → the `compression` key is explicit in the config, and this change's proposal carries the measurements.

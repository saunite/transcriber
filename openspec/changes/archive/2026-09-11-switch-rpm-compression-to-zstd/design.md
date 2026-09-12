## Context

See proposal.md - Why for the measurements. How they were taken, so they can be re-checked:

- **CI attribution** came from run 34656473927's log timestamps, splitting the "Build GUI packages" step by Tauri's own progress lines (`Finished release profile`, each `Bundling …`, `Finished 3 bundles`).
- **The three-way comparison** used a throwaway Cargo project in the session scratchpad (not committed) depending on `rpm = "0.16"`, the same crate `tauri-bundler` uses. It added the real `dist/linux/transcriber-sidecar` and every file in `src-tauri/resources/model/`, built the package once per compression setting, and was measured with `/usr/bin/time -v` on this 8-core machine.
- **Raw compressor throughput** on the same payload, for reference: `gzip -6` 10.1s (29 MB/s), `zstd -3` single-threaded 0.7s (436 MB/s). Both land at 94.8% of the input, because the payload is already-compressed model weights plus a PyInstaller binary.

The gap between those two sets of numbers is the point: inside the `rpm` crate, gzip runs at ~107 KB/s and zstd at ~393 KB/s, hundreds of times slower than the same algorithms standalone. Relevant crate details, in case this is revisited: every variant compresses into an in-memory `Vec<u8>`; `flate2` is used with only its `std` feature, so the pure-Rust `miniz_oxide` backend; and `tauri-bundler` depends on `rpm` with `features = ["bzip2-compression"]`, so `zstdmt` is off and zstd is single-threaded.

## Goals / Non-Goals

**Goals:**
- Cut the dominant cost of the release build with a one-line, reversible configuration change and no change to what ships.

**Non-Goals:**
- The other levers measured in the same session: caching cargo (~2m30s), caching pip for the sidecar freeze (~1m55s), parallelising or trimming the five distro install checks (~3m27s), and building only the AppImage on manual runs. Each is its own small change.
- Patching or replacing the `rpm` crate, or reporting the slowness upstream (worth doing, but not this change).
- Changing the `.deb` or AppImage, which are already 8s and 1m23s.

## Decisions

### 1. Zstd level 3, not `None`

`None` is by far the fastest (4.4s versus 12m25s) and would be tempting, since 5% of a 293 MB package is a poor return for minutes of CPU. It's rejected for now because it changes the artifact users download by +15 MB and relies on every target package manager accepting an uncompressed payload — a compatibility question this change doesn't need to open. Zstd level 3 keeps the artifact byte-for-byte equivalent in size (278.0 vs 278.2 MB) while taking ~15 minutes out of every release, and zstd payloads are the modern default for Fedora and SUSE themselves. If the release build later needs to be faster still, `None` is the next lever, and the install checks are the experiment.

### 2. Level 3, not higher or lower

Level 3 is zstd's own default and sits at the knee of the curve for this payload: the standalone comparison showed level 12 produced 277.9 MB versus level 3's 278.0 MB — 0.1 MB for several times the CPU. Since the payload barely compresses at all, any level above 3 buys nothing here.

### 3. The existing install checks are the safety net

Zstd rpm payloads require RPM 4.14 or newer on the installing system. Rather than assert that Fedora, Leap and Tumbleweed all qualify, the workflow's install checks already install the built `.rpm` in those three containers and fail the leg if any refuses. That converts the compatibility claim into a per-release test, which is why this change needs no new verification machinery.

## Risks / Trade-offs

- **[Risk]** An older RPM-family distro that the install checks don't cover can't read a zstd payload → the checks cover the distros the project supports (`01`'s "Linux release artifacts" requirement names exactly Fedora, Leap and Tumbleweed). Anything older is already excluded by the glibc baseline of the `ubuntu-22.04` builder.
- **[Trade-off]** ~6 minutes of rpm bundling remains, versus 4.4 seconds for `None`. Accepted deliberately to keep the download size unchanged; recorded here so the option isn't lost.
- **[Risk]** The measured 3.7× speedup came from `rpm` 0.16.1 locally, while the CI bundler resolved 0.16.0 → same minor line and the same code paths; task 1.2 confirms the real saving from the next tagged run's timings instead of trusting the extrapolation.

## Context

See proposal.md - Why. The constraints that shape the approach:

- An AppImage is a static ELF runtime with a squashfs filesystem concatenated after it. The released image's runtime header is 944,632 bytes (reported by the image itself via `--appimage-offset`) and its payload is **zstd**-compressed with **131,072-byte** blocks (from `unsquashfs -s`). A squashfs is read-only, so there is no way to remove a file from an AppImage without rebuilding the payload.
- `build_portable.py`'s `build_linux()` currently only globs `src-tauri/target/release/bundle/appimage/*.AppImage`, copies the match into `dist/portable/`, and makes it executable. Both CI (`release.yml`'s "Assemble portable + CLI artifacts" step) and local Linux builds go through it, and it is the last step before an artifact is published.
- The bundling that causes the bug happens inside `linuxdeploy`, which Tauri invokes with no exclusion mechanism: it passes only `OUTPUT`, `ARCH`, `APPIMAGE_EXTRACT_AND_RUN` and `--plugin gtk`. Tauri downloads the plugin script to `~/.cache/tauri/` only when the file is absent, so the plugin's behavior is not configurable from this repo.
- The Linux job's apt list has no `squashfs-tools`; it does install `libfuse2` (for running linuxdeploy's own AppImage).

## Goals / Non-Goals

**Goals:**
- A published Linux portable artifact that starts on a current desktop, fixed in one place that both CI and local builds pass through.
- A repack that cannot silently publish a damaged or bloated image.

**Non-Goals:**
- Changing which libraries `linuxdeploy` bundles, or patching the upstream plugin.
- Fixing the `.deb`/`.rpm`, which are unaffected — they link against host libraries throughout.
- Making the AppImage work on hosts older than the build host. Removing bundled libraries means the host must supply them; that is how AppImage graphics stacks are expected to work, and the build host (Ubuntu 22.04) is already the oldest target.

## Decisions

### 1. Patch the artifact in `build_portable.py`, not in the workflow

`build_linux()` is the single chokepoint every published Linux artifact passes through, so fixing it there covers CI and local builds at once. This is the same reasoning `drop-model-cache-from-bundles` used (its Decision 1): put the fix where the artifact is produced, not in the pipeline that happens to call it.

**Rejected: a step in `release.yml`.** It would fix CI only and leave every local build producing a broken AppImage — the exact split that change rejected.

**Rejected: vendoring a patched `linuxdeploy-plugin-gtk.sh` into `~/.cache/tauri/`.** Tauri only downloads the script when it is missing, so pre-placing a copy would work, but it pins the build to a fork of an upstream file that Tauri otherwise keeps current, in a cache directory that is not part of this repo. Fragile and invisible.

**Rejected: dropping the AppImage target for a plain tarball.** That removes the documented Linux portable form and is a product decision, not a bug fix.

**Rejected: an environment workaround.** Disproven: `WEBKIT_DISABLE_DMABUF_RENDERER=1`, `WEBKIT_DISABLE_COMPOSITING_MODE=1`, and `LIBGL_ALWAYS_SOFTWARE=1` with either all fail identically, because the mismatch is in the library set rather than in WebKit's rendering path.

### 2. Remove exactly two libraries

`usr/lib/libwayland-client.so.0` and `usr/lib/libwayland-egl.so.1`, measured as sufficient: with only those two gone the app runs with zero `EGL_BAD_PARAMETER` aborts and reaches the point of spawning a `WebKitWebProcess`.

**Rejected: also removing `libwayland-cursor`, `libwayland-server` and `libepoxy.so.0`.** They are equally host-owned in principle and arguably should not be bundled either, but they are not implicated in this failure and removing more than the fix needs widens the chance of breaking a host that depends on the bundled copy. The narrow removal is the reversible one. (`libepoxy` is a plausible future suspect if a similar abort reappears — noted for the next investigation, not acted on here.)

**Rejected: deleting the whole GTK immodules directory** (`im-wayland.so`, `im-waylandgtk.so` also came along with the wholesale copy). They are input-method modules, not EGL clients, and they are not involved.

### 3. Rebuild the payload with the input's own squashfs settings

The repack reads the compressor and block size from the input via `unsquashfs -s` and passes them back to `mksquashfs`, rather than hardcoding them. This matters concretely: repacking the zstd/128K payload with `mksquashfs`'s default gzip produced an image **9.7 MB larger**, while matching zstd/128K produced one **24 KB smaller** than the original. Hardcoding would work today and silently inflate every download the day Tauri or linuxdeploy changes compressor. Fall back to zstd/128K if the fields cannot be parsed.

Mechanism, in order: read the runtime length from `<image> --appimage-offset`; `dd` that many bytes into a runtime header file; `unsquashfs -o <offset> -d <dir>` the payload; delete the two libraries; `mksquashfs <dir> <payload> -root-owned -noappend -no-xattrs -comp <comp> -b <block>`; concatenate header and payload; `chmod +x`.

**Rejected: `appimagetool`.** It does exactly this concatenation, but it is another downloaded binary (absent on this machine and on the runner) when `mksquashfs` plus `dd` already suffice.

**Rejected: the image's own `--appimage-extract`.** It works — it is what proved the fix locally — but it executes the artifact and writes `squashfs-root` into the current directory. `unsquashfs -o` needs neither. **This substitution is untested:** the local proof used `--appimage-extract`, so a task must verify the `unsquashfs -o` path end to end rather than assume the two are interchangeable.

### 4. Absence of the libraries is not an error; their presence in the output is

Deleting is best-effort — if a future `linuxdeploy` stops bundling them, the files are simply already gone, which is the desired state and must not fail the build. This mirrors `drop-model-cache-from-bundles`' `ignore_errors=True` reasoning.

The hard checks run on the **output** instead, and any of them fails the build:
1. Neither library appears in the repacked image's file listing.
2. The repacked file's size equals the runtime header plus the payload, so a short write cannot pass. This is not hypothetical: during investigation a full disk produced a truncated 321 MB image that looked plausible, reported a believable size delta, and only failed when run.
3. The repacked image is not dramatically larger than the input (guards a compressor mismatch).

This refines proposal.md, whose first draft said a missing library should fail the build.

### 5. Write the fixed image to `dist/portable/`, leaving the bundler's output untouched

`build_linux()` already copies to `dist/portable/`; the repack happens on the way, in a temporary directory. The bundler's `src-tauri/target/.../bundle/appimage/` original is left alone, so re-running is idempotent and the unpatched image remains for comparison.

## Risks / Trade-offs

- **[Risk]** The host must now supply `libwayland-client`/`libwayland-egl`. → Any system with a working graphical session has them; they are host-owned libraries that upstream's own excludelist says not to bundle. The `.deb`/`.rpm` already rely on host libraries for everything.
- **[Risk]** `unsquashfs -o` behaves differently from the runtime's extractor (permissions, symlinks, executable bits). → Decision 3 calls this out as untested; verification runs the repacked image, which exercises `AppRun`, the hook script and the bundled GTK stack. (Correction to an earlier draft of this line, which asserted `AppRun` is a symlink in the original: it is a regular 274-byte script, alongside `AppRun.wrapped`. The concern was the extractor round-trip, which the verification covers either way.)
- **[Risk]** A future bundler change makes the removal insufficient and the abort returns with a different library. → The output assertions keep the build honest about what shipped, and `libepoxy` is recorded above as the next suspect.
- **[Trade-off]** ~17 s and roughly 800 MB of transient disk per Linux build, for a ~390 MB payload. Irrelevant on a runner; worth knowing locally.
- **[Trade-off]** The repack replaces an artifact produced by a signed-off bundler path with one this repo assembles. Mitigated by changing exactly two files inside it and rebuilding with the input's own settings.

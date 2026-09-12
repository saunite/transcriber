## Why

The released AppImage does not start. It aborts with `Could not create default EGL display: EGL_BAD_PARAMETER. Aborting...` and shows a blank window, while the `.deb` and `.rpm` from the same build run fine. That makes the Linux portable artifact — the only no-install Linux download — unusable, and it blocks `01-add-release-pipeline`'s AppImage verification (task 5.3).

The cause is that the AppImage ships host-owned graphics libraries. `linuxdeploy-plugin-gtk.sh` deploys GTK with `copy_tree "$gtk3_libdir" "$APPDIR/"` — a wholesale copy of the whole GTK library directory — so Ubuntu 22.04's `libwayland-client.so.0` and `libwayland-egl.so.1` end up inside the bundle, and `AppRun` puts them ahead of the host's on `LD_LIBRARY_PATH`. The host's much newer EGL (mesa 26.1.8 on the Fedora 44 test machine) is then forced to use a four-year-old `libwayland-client` and fails at display creation. `libwayland-client` is on upstream's AppImage excludelist, but that list only governs `ldd`-resolved dependency deployment and never applies to a blind directory copy. CI downloads the plugin fresh from `tauri-apps` master on every run, so this is not a stale-tooling problem that a newer version will fix.

## What Changes

- **`build_portable.py`'s `build_linux()` removes the two host-owned libraries from the AppImage** instead of only copying the bundler's output to `dist/portable/`. It extracts the payload, deletes `usr/lib/libwayland-client.so.0` and `usr/lib/libwayland-egl.so.1`, and repacks the image.
- **The repack fails the build loudly** if the finished image is wrong — either library still present, a size that does not match header plus payload, or an unexpected size jump — rather than publishing whatever it produced. A truncated payload must never ship: that happened during this investigation on a full disk and produced a file that looked plausible until it was run. Libraries that are *already* absent are fine and must not fail the build, since a future bundler that stops shipping them is the outcome we want (see design.md Decision 4).
- **`.github/workflows/release.yml` installs `squashfs-tools`**, which the repack needs and the Linux job does not currently have.
- **Nothing else.** The remaining bundled Wayland libraries (`libwayland-cursor`, `libwayland-server`) and `libepoxy.so.0` stay: removing only the two above is measurably sufficient, and a minimal removal is the smaller risk.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
(none — no requirement changes. The behavior this restores is already required: `01-add-release-pipeline`'s `desktop-gui` delta specifies, under "Portable artifact per platform, with native installers alongside", that a Linux user "receive a single executable AppImage file that runs directly once marked executable", and its "Launches without a console or terminal window" requirement expects the window to appear when the AppImage is launched. This change makes the artifact conform to those requirements; it does not alter them.

Note for whoever archives `01`: `openspec/specs/desktop-gui/spec.md` still carries the superseded "Single no-install artifact per platform" requirement, including "SHALL NOT be distributed as an installer package". That is `01`'s un-synced delta, not drift introduced here, and it is left alone deliberately.)

This change sets `skip_specs: true` in `.openspec.yaml`.

## Impact

- **Changed**: `build_portable.py` (`build_linux()`), `.github/workflows/release.yml` (one package added to the Linux job's apt list).
- **Effect**: the Linux portable artifact starts and renders. Verified on Fedora 44 (Wayland/KDE, mesa-libEGL 26.1.8): with those two files removed, the app runs with zero `EGL_BAD_PARAMETER` aborts and spawns a `WebKitWebProcess` — which the abort otherwise prevents, since it kills the app before any web process exists.
- **Size**: neutral. A full extract → delete → repack of the released image produced 389,163,512 bytes against the original's 389,188,088 — 24 KB smaller. (Matching the original's zstd/128K squashfs settings matters: an earlier gzip repack came out 9.7 MB larger.)
- **Unblocks**: `01-add-release-pipeline` task 5.3 (AppImage real-hardware test).
- **Build cost**: one extract-and-repack of a ~390 MB payload per Linux build, ~17 s locally, plus roughly 800 MB of transient disk.
- **Not addressed**: the upstream plugin behavior itself. Worth reporting to `tauri-apps/linuxdeploy-plugin-gtk`, but this change does not depend on an upstream fix.

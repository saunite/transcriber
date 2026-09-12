## 1. Repack the AppImage in the Linux build

- [ ] 1.1 In `build_portable.py`, add a helper that strips the two host-owned libraries from an AppImage and returns the repacked path (design.md Decision 3): read the runtime length from `<image> --appimage-offset`, `dd` that many bytes into a header file, extract the payload with `unsquashfs -o <offset> -d <dir>`, delete `usr/lib/libwayland-client.so.0` and `usr/lib/libwayland-egl.so.1` if present, read the compressor and block size from `unsquashfs -o <offset> -s <image>`, rebuild with `mksquashfs <dir> <payload> -root-owned -noappend -no-xattrs -comp <comp> -b <block>`, concatenate header + payload, and `chmod +x`. Falls back to `zstd`/`131072` when the two fields cannot be parsed. Verify by running it against the released `transcriber_0.1.0_amd64.AppImage` and confirming it exits 0 and produces an executable file.
- [ ] 1.2 Wire it into `build_linux()` so the repack happens on the way to `dist/portable/`, in a temporary directory, leaving `src-tauri/target/.../bundle/appimage/` untouched (design.md Decision 5). Verify `python build_portable.py` on a Linux build still prints/returns the `dist/portable/*.AppImage` path, that the bundler's original is byte-identical to before the run, and that running it twice in a row gives the same result (idempotent).
- [ ] 1.3 Add the three output assertions, each failing the build (design.md Decision 4): neither library present in the repacked image's listing; final size exactly equals header + payload size; repacked size not more than ~5% above the input. Missing input libraries must **not** fail. Verify each guard actually fires: assert on a deliberately truncated payload, and confirm a second run over an already-stripped image succeeds with no libraries to delete.
- [ ] 1.4 Verify the `unsquashfs -o` extraction path end to end, which design.md Decision 3 flags as **untested** — the local proof used the image's own `--appimage-extract`. Confirm the repacked image built via `unsquashfs` runs (window appears, no `EGL_BAD_PARAMETER`), and that `AppRun`, `apprun-hooks/linuxdeploy-plugin-gtk.sh` and the `usr/lib` tree survive extraction with their permissions and symlinks intact (`AppRun` is a symlink in the original).

## 2. CI

- [ ] 2.1 Add `squashfs-tools` to the Linux job's apt install list in `.github/workflows/release.yml` (it provides `mksquashfs`/`unsquashfs`, which the job does not currently have). Verify with `yamllint` plus a YAML parse, and confirm on the next tagged run that the "Assemble portable + CLI artifacts" step does not fail on a missing command.
- [ ] 2.2 On the next tagged run, confirm the published AppImage contains neither `libwayland-client.so.0` nor `libwayland-egl.so.1`, and record the published size against the previous run's ~389 MB to confirm the fix stayed size-neutral. CI is the case that matters — it is where the broken artifact was produced.

## 3. Real-hardware verification

- [ ] 3.1 Download the AppImage from the next tagged run's draft release on the Fedora machine, `chmod +x` it, run it, and confirm the window appears with no `EGL_BAD_PARAMETER` abort — the exact failure this change fixes.
- [ ] 3.2 Transcribe a file through that AppImage and confirm the transcript is written, proving the bundled model and sidecar still resolve after the repack (the model lives in the same `usr/lib` tree the repack rebuilds).
- [ ] 3.3 Tick `01-add-release-pipeline` task 5.3, which this change unblocks, once 3.1 and 3.2 pass.

## 4. Documentation

- [ ] 4.1 Confirm README needs no edit: its AppImage row quotes no size (so the size-neutral fix changes nothing) and the FUSE/`--appimage-extract-and-run` note stays accurate. Record the finding rather than assuming it — check the row and the Linux table, and only edit if something is made wrong.
- [ ] 4.2 Report the wholesale `copy_tree "$gtk3_libdir"` behavior upstream to `tauri-apps/linuxdeploy-plugin-gtk` (host-owned graphics libraries bundled despite being on the AppImage excludelist), and link the issue here. Optional and explicitly not a dependency of this change.

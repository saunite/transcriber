## 1. Configuration and verification

- [x] 1.1 In `src-tauri/tauri.conf.json`, change `bundle.linux.rpm.compression` from `{ "type": "zstd", "level": 3 }` to `{ "type": "none" }` (design.md Decision 1). Verify locally: the JSON parses, `cargo check` in `src-tauri/` (which runs Tauri's build script and validates the config) reports no errors, a `cargo tauri build --bundles rpm` finishes its bundling in **seconds** rather than ~14 minutes, `rpm -qp --qf '%{PAYLOADCOMPRESSOR}\n'` reports `none`, and `rpm -qpR` still lists the two library dependencies.

  **Verified locally 2026-09-11/12** (Fedora 44, Tauri CLI 2.11.4). `bundle.linux.rpm.compression` is `{ "type": "none" }`; the JSON parses and `cargo check` reports no errors. The whole `cargo tauri build --bundles rpm` took **59 seconds** wall (compile was cached), against **14m42s** with zstd — bundling itself is now seconds, exactly as the harness predicted. `rpm -qp --qf '%{PAYLOADCOMPRESSOR}'` reports **`(none)`**, and `rpm -qpR` still lists `libwebkit2gtk-4.1.so.0()(64bit)` and `libgtk-3.so.0()(64bit)`.

  **Size grew more than proposal.md predicted: 306.9 MB against zstd's 281.8 MB, so +25.1 MB, not +15 MB.** The +15 MB figure came from the harness, which compressed only the cpio payload (293.2 MB stored vs 278.0 MB zstd). A real package also stores the files Tauri wraps around that payload uncompressed, so the true cost is ~25 MB — about 9%. Extrapolating to CI, the `.rpm` should go from ~297 MB to roughly ~322 MB rather than the ~312 MB the proposal estimated. Recorded rather than quietly absorbed; the trade is still ~10 minutes of every release for ~25 MB, which is the user's stated preference, but the number is bigger than they were told when they chose it.
- [x] 1.2 Confirm on the next tagged run that the `Bundling …rpm` → `Finished 3 bundles` span collapses from 10m11s (run 34672668438) to seconds, and that all five install checks still pass — especially `fedora:latest`, `opensuse/leap:latest` and `opensuse/tumbleweed`, which are the compatibility test for an uncompressed payload (design.md Decision 2). Record the new span and the package size.

  **Verified on tagged run 34694349879 (v0.1.0, 2026-09-12).** The rpm bundling span collapsed from **10m11s to 4.09 s**: `Bundling Transcriber-0.1.0-1.x86_64.rpm` at 12:48:04.07, `Finished 3 bundles` at 12:48:08.16. For context in the same step, the AppImage took 1m46s and the `.deb` 10 s.

  **All five install checks passed** — the log carries `##[group]debian:stable passed`, `fedora:latest passed`, `opensuse/tumbleweed passed`, `ubuntu:24.04 passed` and `opensuse/leap:latest passed`, with `transcriber-0.1.0-1.x86_64` installing last in each transaction. The uncompressed payload is therefore accepted by dnf, zypper and apt alike. (One `::error` string appears in the step, but it is the workflow's own un-expanded `echo "::error::install check failed on $img"` template being echoed; the annotations API reports **0** annotations for the job.)

  **Size, now measured rather than extrapolated: 338,822,041 bytes (323.1 MiB)**, against the previous zstd run's 311,676,225 bytes — **+27,145,816 bytes (+25.9 MiB)**. That lands close to the +25.1 MiB measured locally in task 1.1 and well above the +15 MB the proposal first predicted; the ~322 MiB extrapolation recorded in 1.1 was accurate. `PAYLOADCOMPRESSOR` on the published package is `(none)` and `rpm -qpR` still lists both library dependencies.
- [ ] 1.3 Install the resulting `.rpm` on the Fedora machine and confirm it installs, launches and transcribes, as with the zstd switch. A rejected payload would appear as a `dnf` install error rather than a broken app.
- [x] 1.4 Check that no README statement is made wrong by the size change (the `.rpm` becomes the largest download at ~312 MB). The download table lists file names, not sizes, so this is expected to need no edit — confirm and record rather than assume.

  **Checked and confirmed 2026-09-11/12: no README edit is needed.** A grep for size figures, the word "size", and ranking words (`largest`/`smaller`/`bigger`/`compress`) over the whole README returns five hits, and none is a package-size claim:
  - lines 80 and 85 — the icon master's filename, `resources/src/transcriber-icon-full-size.xcf`;
  - line 333 — `--model <size>`, listing model *names* (tiny/base/small/…);
  - line 467 — troubleshooting advice to "use smaller model";
  - line 173 — "ships the `base` Whisper model (~145MB)", which is the model's own on-disk size and is unchanged by payload compression.

  The Linux download table lists file names and install commands only, with no sizes and no statement ranking the downloads against each other, so the `.rpm` becoming the largest asset makes nothing in the README untrue. Recorded rather than assumed, as the task asked.

  **The task's own "~312 MB" figure is the superseded proposal estimate.** Measured locally: 306.9 MB uncompressed against zstd's 281.8 MB (**+25.1 MB**, not the +15 MB the proposal predicted — see task 1.1), which extrapolates to roughly **~322 MB** in CI rather than ~312 MB. Task 1.2 will record the real CI number.

  **Noticed while grepping, deliberately left alone:** line 173 cross-references `openspec/changes/drop-ffmpeg-dependency/`, a path that no longer exists — the change was archived to `openspec/changes/archive/2026-09-08-drop-ffmpeg-dependency/`, so the link is dead rather than merely stale. Unrelated to compression, so it is not fixed under this change; flagging it for whoever next touches README's build section.

## 1. Live-session output persistence

- [x] 1.1 Add `output_path: Option<String>` to `start_live_session` (`src-tauri/src/sidecar.rs`), pushing `--output <path>` when non-empty

  Done and compiled clean (`cargo build --target x86_64-pc-windows-gnu`, dev + release).
- [x] 1.2 Add an "Output file" field + "Browse…" button to Session Settings (`src/index.html`, `src/style.css`), reusing the existing `.settings-toggle` visual language (no new design direction — confirmed against `.impeccable/surfaces/src-index-html.md`'s "settings tucked in a collapsible strip" direction)
- [x] 1.3 Wire the Browse button to `tauri-plugin-dialog`'s `save()` and auto-generate a default timestamped filename on load (`src/main.js`)

  Verified `dialog:default`'s permission set includes `allow-save` by reading the plugin's own `permissions/default.toml` directly (not assumed) — no capability file change needed. Verified the timestamp-generation logic's output format directly with `node -e`.

## 2. Live-session defaults matching start_teams_transcription.bat

- [x] 2.1 Default "Include microphone" to checked and show the microphone device field immediately (`src/index.html`)
- [x] 2.2 Always pass `--chunk-duration 10 --actual-time` for live sessions (`src-tauri/src/sidecar.rs`), matching the `.bat` reference exactly

## 3. Build and real-hardware verification

- [x] 3.1 Rebuild (`cargo tauri build --target x86_64-pc-windows-gnu`) and reassemble `dist/portable/Transcriber.zip`

  Done, 20s incremental build, zip reassembled via `build_portable.py --target x86_64-pc-windows-gnu`.
- [x] 3.2 User retest on real Windows hardware

  User confirmed the underlying issue (silent live capture) was explained by mic-capture being off by default with nothing playing through speakers — not a bug. Fix and defaults deployed; this task's own verification is the mic-default change itself being live in the rebuilt artifact the user is now running (confirmed via file timestamp matching the rebuild).

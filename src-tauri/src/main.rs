// UNVERIFIED: written without a working Rust/Cargo toolchain on this
// machine (see openspec/changes/add-tauri-gui/design.md). Treat as a
// first draft to `cargo build` and iterate on.

mod sidecar;

use sidecar::SidecarManager;
use std::sync::Mutex;

pub struct AppState {
    pub sidecar: Mutex<SidecarManager>,
}

#[tauri::command]
fn get_platform() -> &'static str {
    // Used by src/main.js to gate live-capture controls on macOS
    // (specs/desktop-gui "Graceful macOS degradation") until
    // add-macos-capture's hardware verification is complete.
    std::env::consts::OS
}

fn main() {
    // No sidecar spawn and no model load happen here -- the window must be
    // shown and interactive immediately regardless of engine/model load
    // time (design.md Decision 3 & 4, specs/desktop-gui "Fast, non-blocking
    // app open"). The sidecar is only ever spawned from a command in
    // sidecar.rs, invoked by user action in the UI.
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(AppState {
            sidecar: Mutex::new(SidecarManager::new()),
        })
        .invoke_handler(tauri::generate_handler![
            get_platform,
            sidecar::start_live_session,
            sidecar::stop_live_session,
            sidecar::start_file_transcription,
            sidecar::list_devices,
        ])
        .run(tauri::generate_context!())
        .expect("error while running transcriber GUI");
}

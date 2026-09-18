#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod sidecar;
mod update;

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
    // The Wayland app ID and X11 window class both come from GLib's program
    // name, which is the binary name (transcriber-gui) unless set first. Naming
    // it Transcriber matches Transcriber.desktop, so the desktop finds the icon
    // (openspec/changes/fix-linux-native-window-frame, design.md Decision 3).
    #[cfg(target_os = "linux")]
    gtk::glib::set_prgname(Some("Transcriber"));

    // No sidecar spawn and no model load happen here -- the window must be
    // shown and interactive immediately regardless of engine/model load
    // time (design.md Decision 3 & 4, specs/desktop-gui "Fast, non-blocking
    // app open"). The sidecar is only ever spawned from a command in
    // sidecar.rs, invoked by user action in the UI.
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(AppState {
            sidecar: Mutex::new(SidecarManager::new()),
        })
        // Leftover unpacked engine copies from killed runs, removed in the
        // background so the window still opens at once
        // (openspec/changes/fix-sidecar-temp-leak).
        .setup(|_app| {
            tauri::async_runtime::spawn_blocking(|| sidecar::remove_stale_extractions(&std::env::temp_dir()));
            // On Wayland tao gives every window its own header bar, which forces
            // client-side decorations with a fixed button layout. Removing it lets
            // KWin draw the frame on KDE and GTK draw its standard one elsewhere.
            // GTK settles this when the window is first shown, so tauri.linux.conf.json
            // starts it hidden (openspec/changes/fix-linux-native-window-frame).
            #[cfg(target_os = "linux")]
            {
                use gtk::prelude::GtkWindowExt;
                use tauri::Manager;
                if let Some(window) = _app.get_webview_window("main") {
                    window.gtk_window()?.set_titlebar(None::<&gtk::Widget>);
                    window.show()?;
                }
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_platform,
            sidecar::start_live_session,
            sidecar::stop_live_session,
            sidecar::start_file_transcription,
            sidecar::list_devices,
            update::check_for_update,
            update::open_releases_page,
        ])
        .build(tauri::generate_context!())
        .expect("error while building transcriber GUI")
        // Closing the app must not leave an engine capturing or transcribing
        // (specs/desktop-gui "SHALL stop it cleanly on user request or app quit").
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                sidecar::stop_all_engines(app);
            }
        });
}

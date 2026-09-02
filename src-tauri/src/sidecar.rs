//! Sidecar process management for the bundled Python transcription engine.
//!
//! UNVERIFIED: written without a working Rust/Cargo toolchain available on
//! this machine (see openspec/changes/add-tauri-gui/design.md and
//! tasks.md). Matches the Tauri v2 `tauri-plugin-shell` sidecar API as
//! documented at authoring time; treat as a first draft to compile and
//! iterate on, not confirmed-working code.
//!
//! On-demand spawn only (never called at app startup -- see main.rs and
//! specs/desktop-gui/spec.md "Fast, non-blocking app open"). Transcript
//! lines are parsed from the sidecar's existing stdout format rather than
//! a new protocol (design.md Decision 2); the regex below is the Rust
//! twin of the one verified against real engine output in
//! test_transcript_line_format.py.

use once_cell::sync::Lazy;
use regex::Regex;
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, Manager, State};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

use crate::AppState;

/// Mirrors openspec/changes/add-tauri-gui/design.md (Decision 2) and
/// test_transcript_line_format.py's TRANSCRIPT_LINE_REGEX.
static TRANSCRIPT_LINE_RE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^\[(?P<ts>[^\]]+)\](?:\s\[(?P<tag>SYS|MIC)\])?\s(?P<text>.*)$").unwrap()
});

/// Logical name registered under `bundle.externalBin` in tauri.conf.json.
const SIDECAR_NAME: &str = "transcriber-sidecar";

/// Resolves the bundled model directory relative to the running app's own
/// location via Tauri's path API, so this works identically whether the app
/// is installed (NSIS) or run from a portable, extract-anywhere folder --
/// see openspec/changes/add-portable-build/design.md Decision 1. Mirrors
/// `bundle.resources: ["resources/model/**/*"]` in tauri.conf.json, which
/// preserves that relative path under the resolved resource directory.
fn resolve_model_dir(app: &AppHandle) -> Result<String, String> {
    let dir = app
        .path()
        .resource_dir()
        .map_err(|e| format!("could not resolve bundled resource directory: {e}"))?
        .join("resources")
        .join("model");
    let dir = dir.to_string_lossy().into_owned();
    // ponytail: Tauri's resource_dir() canonicalizes to a `\\?\`-prefixed
    // extended-length path on Windows; ctranslate2 (faster-whisper's C++
    // backend) can't open files through that prefix ("Unable to open file
    // 'model.bin'" -- verified by reproducing with/without the prefix
    // directly against the sidecar). Strip it; strip_prefix is a no-op on
    // other OSes where the prefix never appears.
    Ok(dir.strip_prefix(r"\\?\").unwrap_or(&dir).to_string())
}

pub struct SidecarManager {
    child: Option<CommandChild>,
    session_active: bool,
}

impl SidecarManager {
    pub fn new() -> Self {
        Self {
            child: None,
            session_active: false,
        }
    }
}

#[derive(Clone, Serialize)]
struct TranscriptLinePayload {
    ts: String,
    tag: Option<String>,
    text: String,
}

#[derive(Clone, Serialize)]
struct SidecarLogPayload {
    line: String,
}

#[derive(Clone, Serialize)]
struct SidecarCrashedPayload {
    message: String,
}

#[derive(Clone, Deserialize, Serialize)]
pub struct DeviceInfo {
    index: u32,
    name: String,
    max_input_channels: u32,
    default_samplerate: f64,
}

/// Reads sidecar stdout/stderr on a background task and turns each line
/// into a `transcript-line` or `sidecar-log` event -- never blocks the UI
/// thread (specs/desktop-gui "UI remains responsive during sidecar
/// activity"). `mark_inactive_on_exit` distinguishes a live session
/// (tracked in SidecarManager, eligible for crash detection) from a
/// one-shot file transcription (not tracked as an active session).
fn spawn_sidecar_events(
    app: AppHandle,
    mut rx: tauri::async_runtime::Receiver<CommandEvent>,
    mark_inactive_on_exit: bool,
) {
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let line = String::from_utf8_lossy(&bytes).trim_end().to_string();
                    if let Some(captures) = TRANSCRIPT_LINE_RE.captures(&line) {
                        let payload = TranscriptLinePayload {
                            ts: captures
                                .name("ts")
                                .map(|m| m.as_str().to_string())
                                .unwrap_or_default(),
                            tag: captures.name("tag").map(|m| m.as_str().to_string()),
                            text: captures
                                .name("text")
                                .map(|m| m.as_str().to_string())
                                .unwrap_or_default(),
                        };
                        let _ = app.emit("transcript-line", payload);
                    } else if !line.trim().is_empty() {
                        let _ = app.emit("sidecar-log", SidecarLogPayload { line });
                    }
                }
                CommandEvent::Stderr(bytes) => {
                    let line = String::from_utf8_lossy(&bytes).trim_end().to_string();
                    if !line.is_empty() {
                        let _ = app.emit("sidecar-log", SidecarLogPayload { line });
                    }
                }
                CommandEvent::Terminated(payload) => {
                    if mark_inactive_on_exit {
                        if let Some(state) = app.try_state::<AppState>() {
                            let mut sidecar = state.sidecar.lock().unwrap();
                            let was_active = sidecar.session_active;
                            sidecar.session_active = false;
                            sidecar.child = None;
                            if was_active && payload.code != Some(0) {
                                // Crash detection: an active session's sidecar
                                // exited without being asked to (specs/desktop-gui
                                // "Sidecar crashes mid-session").
                                let _ = app.emit(
                                    "sidecar-crashed",
                                    SidecarCrashedPayload {
                                        message: format!(
                                            "Capture engine exited unexpectedly (code {:?}).",
                                            payload.code
                                        ),
                                    },
                                );
                            }
                        }
                    } else {
                        // One-shot file transcription: tell the UI the run
                        // finished so it can clear the progress indicator
                        // (specs/desktop-gui "File transcription via
                        // drag-and-drop ... showing progress").
                        let _ = app.emit("file-transcription-complete", payload.code == Some(0));
                    }
                    break;
                }
                _ => {}
            }
        }
    });
}

#[tauri::command]
pub async fn start_live_session(
    app: AppHandle,
    state: State<'_, AppState>,
    model: String,
    language: Option<String>,
    include_mic: bool,
    mic_device: Option<i32>,
) -> Result<(), String> {
    let mut args = vec![
        "--live".to_string(),
        "--wasapi".to_string(),
        "--model".to_string(),
        model,
        "--model-path".to_string(),
        resolve_model_dir(&app)?,
    ];
    // ponytail: hardcodes --wasapi (Windows). --coreaudio-tap (macOS) and
    // Linux's flag-less simple mode need the same branch here once the
    // platform-gate (tasks.md 5.8) is lifted for a given OS -- this
    // command isn't reachable from the UI on macOS yet (see main.rs
    // get_platform / src/main.js), so it's scoped to Windows for now.
    if let Some(lang) = language {
        args.push("--language".to_string());
        args.push(lang);
    }
    if include_mic {
        args.push("--include-mic".to_string());
        if let Some(dev) = mic_device {
            args.push("--mic-device".to_string());
            args.push(dev.to_string());
        }
    }

    let sidecar_command = app
        .shell()
        .sidecar(SIDECAR_NAME)
        .map_err(|e| e.to_string())?
        .args(args);
    let (rx, child) = sidecar_command.spawn().map_err(|e| e.to_string())?;

    {
        let mut sidecar = state.sidecar.lock().unwrap();
        sidecar.child = Some(child);
        sidecar.session_active = true;
    }

    spawn_sidecar_events(app, rx, true);
    Ok(())
}

#[tauri::command]
pub async fn stop_live_session(state: State<'_, AppState>) -> Result<(), String> {
    let mut sidecar = state.sidecar.lock().unwrap();
    sidecar.session_active = false;
    if let Some(child) = sidecar.child.take() {
        // ponytail: hard kill, no graceful SIGINT relay -- tauri-plugin-shell
        // does not expose a portable "send Ctrl+C to child" primitive as of
        // writing, and transcriber.py's graceful shutdown is a SIGINT
        // handler. Upgrade path: a stdin-based stop protocol in
        // transcriber.py if abrupt termination is found to drop buffered
        // transcript lines or leave partial WAV files in practice.
        #[cfg(windows)]
        {
            // PyInstaller's --onefile bootloader relaunches into a child
            // process on Windows (extracts to a temp dir, then execs into
            // it); child.kill() below only terminates that bootloader and
            // orphans the actual worker process, which keeps running and
            // holding the audio device -- verified by stopping a live
            // session and finding transcriber-sidecar.exe still alive
            // afterward. taskkill /T kills the whole process tree instead.
            let _ = std::process::Command::new("taskkill")
                .args(["/F", "/T", "/PID", &child.pid().to_string()])
                .output();
        }
        #[cfg(not(windows))]
        child.kill().map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
pub async fn start_file_transcription(
    app: AppHandle,
    file_path: String,
    format: String,
    task: String,
    model: String,
    language: Option<String>,
) -> Result<(), String> {
    let mut args = vec![
        "--file".to_string(), file_path,
        "--format".to_string(), format,
        "--task".to_string(), task,
        "--model".to_string(), model,
        "--model-path".to_string(), resolve_model_dir(&app)?,
    ];
    if let Some(lang) = language {
        args.push("--language".to_string());
        args.push(lang);
    }
    let sidecar_command = app
        .shell()
        .sidecar(SIDECAR_NAME)
        .map_err(|e| e.to_string())?
        .args(args);
    let (rx, _child) = sidecar_command.spawn().map_err(|e| e.to_string())?;
    // Not tracked in SidecarManager / not eligible for crash-detection --
    // file transcription is a one-shot run, not a long-lived session.
    spawn_sidecar_events(app, rx, false);
    Ok(())
}

#[tauri::command]
pub async fn list_devices(app: AppHandle) -> Result<Vec<DeviceInfo>, String> {
    let sidecar_command = app
        .shell()
        .sidecar(SIDECAR_NAME)
        .map_err(|e| e.to_string())?
        .args(["--list-devices-json"]);
    let output = sidecar_command
        .output()
        .await
        .map_err(|e| e.to_string())?;
    let stdout = String::from_utf8_lossy(&output.stdout);
    serde_json::from_str(&stdout).map_err(|e| e.to_string())
}

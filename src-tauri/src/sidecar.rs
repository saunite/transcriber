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

/// Strips Windows' `\\?\`-prefixed extended-length path forms down to a
/// path ctranslate2 (faster-whisper's C++ backend) can actually open --
/// verified by reproducing "Unable to open file 'model.bin'" with the
/// prefix present and confirming it opens fine without it. A no-op on
/// other OSes and on already-plain Windows paths, where the prefix never
/// appears.
///
/// Windows has two extended-length forms: `\\?\C:\...` for local drives
/// and `\\?\UNC\server\share\...` for network paths (e.g. running from
/// \\wsl.localhost\... during WSL-based development/testing, or any
/// network-mapped install location). Stripping only `\\?\` from the UNC
/// form leaves the literal text `UNC\server\share\...`, not a valid path
/// (it needs `\\server\share\...`) -- reproduced for real: a Windows build
/// run from a WSL-mounted checkout failed with `FileNotFoundError:
/// --model-path UNC\wsl.localhost\...\model does not exist`.
fn strip_extended_length_prefix(dir: &str) -> String {
    let dir = dir.strip_prefix(r"\\?\").unwrap_or(dir);
    match dir.strip_prefix(r"UNC\") {
        Some(unc_rest) => format!(r"\\{unc_rest}"),
        None => dir.to_string(),
    }
}

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
    Ok(strip_extended_length_prefix(&dir.to_string_lossy()))
}

#[cfg(test)]
mod tests {

    /// Both outcomes of a stop attempt, with fabricated PIDs.
    ///
    /// Deliberately NOT done by calling terminate_process_tree(1) as the task
    /// suggested: that would enumerate every child of init and signal them
    /// all. Most would fail with EPERM, but a user-owned process parented to
    /// PID 1 could genuinely be killed -- an unacceptable way to test a log
    /// message.
    #[cfg(not(windows))]
    #[test]
    fn stop_result_reports_success_only_with_no_survivors() {
        assert_eq!(stop_result_line(&[]), "Capture engine stopped.");

        let line = stop_result_line(&[4242, 4243]);
        assert!(line.contains("Failed to stop"), "{line}");
        assert!(line.contains("4242") && line.contains("4243"), "{line}");
        assert!(
            line.contains("may still be active"),
            "a failed stop must warn that capture may continue: {line}"
        );
    }


    /// The defect this guards against: PyInstaller's --onefile bootloader
    /// re-executes into a worker, and stopping used to signal only the PID we
    /// launched, leaving that worker holding the audio device
    /// (openspec/changes/fix-live-stop-orphans-engine). A shell spawning a
    /// child stands in for that shape -- no audio hardware needed.
    #[cfg(not(windows))]
    #[test]
    fn finds_and_terminates_a_whole_process_tree() {
        let mut parent = std::process::Command::new("sh")
            .args(["-c", "sleep 60 & sleep 60"])
            .spawn()
            .expect("spawn stand-in tree");
        let parent_pid = parent.id();

        // Give the shell a moment to fork its children.
        let deadline = std::time::Instant::now() + std::time::Duration::from_secs(5);
        let mut kids = Vec::new();
        while std::time::Instant::now() < deadline {
            kids = descendant_pids(parent_pid);
            if !kids.is_empty() {
                break;
            }
            std::thread::sleep(std::time::Duration::from_millis(50));
        }
        assert!(
            !kids.is_empty(),
            "descendant_pids found no children of {parent_pid}; the tree walk is broken, \
             which is exactly how the orphaned-worker bug survived"
        );
        assert!(kids.iter().all(|p| pid_alive(*p)), "children should be alive before the stop");

        let survivors = terminate_process_tree(parent_pid);
        assert!(
            survivors.is_empty(),
            "processes survived the stop: {survivors:?} -- a stop that leaves survivors must \
             never be reported as success"
        );
        for pid in &kids {
            assert!(!pid_alive(*pid), "child {pid} outlived terminate_process_tree");
        }
        let _ = parent.wait();
    }

    #[cfg(not(windows))]
    #[test]
    fn pid_alive_distinguishes_live_from_dead() {
        assert!(pid_alive(std::process::id()), "this test's own process must read as alive");

        let mut doomed = std::process::Command::new("sh")
            .args(["-c", "exit 0"])
            .spawn()
            .expect("spawn short-lived process");
        let pid = doomed.id();
        let _ = doomed.wait(); // reaped, so the PID is gone rather than a zombie
        assert!(!pid_alive(pid), "a reaped process must not read as alive");
    }

    use super::{build_live_session_args, strip_extended_length_prefix};
    // cfg-gated to match the helpers themselves, which only exist off Windows.
    #[cfg(not(windows))]
    use super::{descendant_pids, pid_alive, stop_result_line, terminate_process_tree};

    #[test]
    fn strips_local_drive_extended_prefix() {
        assert_eq!(
            strip_extended_length_prefix(r"\\?\C:\Users\me\Transcriber\resources\model"),
            r"C:\Users\me\Transcriber\resources\model"
        );
    }

    #[test]
    fn strips_unc_extended_prefix_to_valid_unc_path() {
        assert_eq!(
            strip_extended_length_prefix(
                r"\\?\UNC\wsl.localhost\Ubuntu\home\andre\repos\transcriber\resources\model"
            ),
            r"\\wsl.localhost\Ubuntu\home\andre\repos\transcriber\resources\model"
        );
    }

    #[test]
    fn passes_through_plain_paths_unchanged() {
        assert_eq!(
            strip_extended_length_prefix(r"C:\Users\me\Transcriber\resources\model"),
            r"C:\Users\me\Transcriber\resources\model"
        );
        assert_eq!(
            strip_extended_length_prefix("/home/andre/repos/transcriber/resources/model"),
            "/home/andre/repos/transcriber/resources/model"
        );
    }

    #[test]
    fn passes_only_this_platforms_capture_flag() {
        // --wasapi on Linux made the sidecar refuse to start
        // (openspec/changes/fix-gui-file-queue-and-linux-live).
        let args = build_live_session_args(
            "base".to_string(),
            "/model/dir".to_string(),
            None,
            false,
            None,
            None,
            None,
        );
        assert_eq!(args[0], "--live");
        assert_eq!(args.contains(&"--wasapi".to_string()), cfg!(windows), "{args:?}");
        assert_eq!(args.contains(&"--coreaudio-tap".to_string()), cfg!(target_os = "macos"), "{args:?}");
    }

    #[test]
    fn omits_audio_device_when_unset() {
        let args = build_live_session_args(
            "base".to_string(),
            "/model/dir".to_string(),
            None,
            false,
            None,
            None,
            None,
        );
        assert!(
            !args.contains(&"--audio-device".to_string()),
            "auto-detect (today's default) must stay untouched when no override is given: {args:?}"
        );
    }

    #[test]
    fn passes_audio_device_override_when_set() {
        let args = build_live_session_args(
            "base".to_string(),
            "/model/dir".to_string(),
            None,
            false,
            None,
            None,
            Some(7),
        );
        let idx = args
            .iter()
            .position(|a| a == "--audio-device")
            .expect("--audio-device should be present when overridden");
        assert_eq!(args[idx + 1], "7");
    }

    #[test]
    fn omits_language_when_auto_detect() {
        let args = build_live_session_args(
            "base".to_string(),
            "/model/dir".to_string(),
            None,
            false,
            None,
            None,
            None,
        );
        assert!(
            !args.contains(&"--language".to_string()),
            "auto-detect (empty selection) must omit --language entirely: {args:?}"
        );
    }

    #[test]
    fn passes_language_when_selected() {
        let args = build_live_session_args(
            "base".to_string(),
            "/model/dir".to_string(),
            Some("en".to_string()),
            false,
            None,
            None,
            None,
        );
        let idx = args
            .iter()
            .position(|a| a == "--language")
            .expect("--language should be present when a language is selected");
        assert_eq!(args[idx + 1], "en");
    }

    // The frontend re-stamps the output path on every start
    // (`withFreshTimestamp()` in src/main.js) so a second session can never
    // truncate the first one's transcript. That only holds if this layer
    // forwards the stamped path verbatim -- any normalising or re-deriving
    // here would collapse two distinct sessions back onto one file.
    #[test]
    fn forwards_stamped_output_path_verbatim() {
        let stamped = "transcript_20260909_143012.txt";
        let args = build_live_session_args(
            "base".to_string(),
            "/model/dir".to_string(),
            None,
            false,
            None,
            Some(stamped.to_string()),
            None,
        );
        let idx = args
            .iter()
            .position(|a| a == "--output")
            .expect("--output should be present when the frontend supplies a path");
        assert_eq!(args[idx + 1], stamped);
    }

    #[test]
    fn omits_output_when_empty_rather_than_passing_a_blank_path() {
        let args = build_live_session_args(
            "base".to_string(),
            "/model/dir".to_string(),
            None,
            false,
            None,
            Some(String::new()),
            None,
        );
        assert!(
            !args.contains(&"--output".to_string()),
            "an empty field must fall through to the engine's own default, not pass --output \"\": {args:?}"
        );
    }
}

pub struct SidecarManager {
    child: Option<CommandChild>,
    session_active: bool,
    /// A one-shot file run's process. Tracked so it can be terminated on
    /// quit and so a live session cannot start beside it -- it used to be
    /// dropped on the floor (`let (rx, _child) = ...`), which made a file
    /// run unstoppable by design
    /// (openspec/changes/fix-live-stop-orphans-engine).
    file_child: Option<CommandChild>,
}

impl SidecarManager {
    pub fn new() -> Self {
        Self {
            child: None,
            session_active: false,
            file_child: None,
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

/// Builds `start_live_session`'s sidecar argument list. Pulled out of the
/// `#[tauri::command]` itself (which needs a live `AppHandle` for
/// `resolve_model_dir()`, unavailable in a unit test) so the actual
/// flag-assembly logic -- what's always-on, what's conditional, what's
/// omitted by default -- is directly testable.
///
/// The capture flag follows the OS this binary was built for -- the GUI only
/// ever runs there (openspec/changes/fix-gui-file-queue-and-linux-live):
/// WASAPI loopback on Windows, the Core Audio tap on macOS (unreachable while
/// the macOS live-capture gate in src/main.js is on), and none on Linux, whose
/// default --live path already captures system audio + microphone.
fn build_live_session_args(
    model: String,
    model_dir: String,
    language: Option<String>,
    include_mic: bool,
    mic_device: Option<i32>,
    output_path: Option<String>,
    audio_device: Option<i32>,
) -> Vec<String> {
    let mut args = vec!["--live".to_string()];
    if cfg!(windows) {
        args.push("--wasapi".to_string());
    } else if cfg!(target_os = "macos") {
        args.push("--coreaudio-tap".to_string());
    }
    args.extend([
        "--model".to_string(),
        model,
        "--model-path".to_string(),
        model_dir,
        // Mirrors win-start-transcription.bat's default invocation:
        // --chunk-duration 10 --actual-time. Not user-configurable (the
        // .bat doesn't expose them either) -- output_path and audio_device
        // below are the pieces of that invocation this UI does let the
        // user override.
        "--chunk-duration".to_string(),
        "10".to_string(),
        "--actual-time".to_string(),
    ]);
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
    if let Some(path) = output_path.filter(|p| !p.is_empty()) {
        args.push("--output".to_string());
        args.push(path);
    }
    // Advanced, discouraged override of the auto-detected WASAPI loopback
    // device (openspec/changes/add-wasapi-device-override) -- omitted
    // entirely when unset, so auto-detection (transcriber.py's own
    // `args.audio_device >= 0` check) is untouched by default.
    if let Some(dev) = audio_device {
        args.push("--audio-device".to_string());
        args.push(dev.to_string());
    }
    args
}

#[tauri::command]
pub async fn start_live_session(
    app: AppHandle,
    state: State<'_, AppState>,
    model: String,
    language: Option<String>,
    include_mic: bool,
    mic_device: Option<i32>,
    output_path: Option<String>,
    audio_device: Option<i32>,
) -> Result<(), String> {
    let model_dir = resolve_model_dir(&app)?;
    let args = build_live_session_args(
        model,
        model_dir,
        language,
        include_mic,
        mic_device,
        output_path,
        audio_device,
    );

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

/// Descendant PIDs of `pid`, one level deep and then recursively.
///
/// PyInstaller's --onefile bootloader re-executes into a worker process, and
/// that worker is what holds the audio device. Killing only the PID we
/// launched leaves it capturing -- the exact failure the Windows branch of
/// `stop_live_session` already documents and fixes with `taskkill /T`
/// (openspec/changes/fix-live-stop-orphans-engine design.md Decision 1).
///
/// Linux exposes children directly under /proc; elsewhere (macOS) `pgrep -P`
/// is used, which exists on both. Signal-then-recheck covers the race where
/// a process forks again between listing and signalling.
#[cfg(not(windows))]
fn descendant_pids(pid: u32) -> Vec<u32> {
    fn children_of(pid: u32) -> Vec<u32> {
        let mut out = Vec::new();
        let task_dir = format!("/proc/{pid}/task");
        if let Ok(entries) = std::fs::read_dir(&task_dir) {
            for entry in entries.flatten() {
                let path = entry.path().join("children");
                if let Ok(text) = std::fs::read_to_string(path) {
                    out.extend(text.split_whitespace().filter_map(|t| t.parse::<u32>().ok()));
                }
            }
        }
        if out.is_empty() {
            // No /proc (macOS) or an unreadable one.
            if let Ok(output) = std::process::Command::new("pgrep")
                .args(["-P", &pid.to_string()])
                .output()
            {
                out.extend(
                    String::from_utf8_lossy(&output.stdout)
                        .split_whitespace()
                        .filter_map(|t| t.parse::<u32>().ok()),
                );
            }
        }
        out.sort_unstable();
        out.dedup();
        out
    }

    let mut found = Vec::new();
    let mut frontier = children_of(pid);
    // Depth-bounded: the bootloader spawns one worker, and the engine's own
    // multiprocessing children sit under that. A cycle is impossible in a
    // process tree, but the bound keeps a pathological /proc read finite.
    for _ in 0..8 {
        if frontier.is_empty() {
            break;
        }
        let mut next = Vec::new();
        for child in frontier.drain(..) {
            if !found.contains(&child) {
                found.push(child);
                next.extend(children_of(child));
            }
        }
        frontier = next;
    }
    found
}

/// True if the process is still alive *and holding resources* -- which makes
/// "did the stop actually work?" answerable rather than assumed
/// (design.md Decision 3).
///
/// `kill -0` alone is not enough: it succeeds for a **zombie**, and a zombie
/// is an already-dead process awaiting reap by whoever spawned it
/// (tauri-plugin-shell's event pump here, `wait()` in a test). It holds no
/// audio device, so counting one as a survivor would report a successful
/// stop as a failure -- the original bug's dishonesty in reverse. Verified:
/// a SIGKILLed child read as alive under `kill -0` until it was reaped.
#[cfg(not(windows))]
fn pid_alive(pid: u32) -> bool {
    match std::process::Command::new("ps")
        .args(["-o", "stat=", "-p", &pid.to_string()])
        .output()
    {
        Ok(output) if output.status.success() => {
            let stat = String::from_utf8_lossy(&output.stdout);
            let stat = stat.trim();
            // Empty means ps printed nothing for the pid; 'Z' is a zombie.
            !stat.is_empty() && !stat.starts_with('Z')
        }
        // ps ran and found no such process.
        Ok(_) => false,
        // ps is missing: fall back to existence, which is better than
        // declaring every process dead and reporting a false success.
        Err(_) => std::process::Command::new("kill")
            .args(["-0", &pid.to_string()])
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false),
    }
}

#[cfg(not(windows))]
fn signal_pids(sig: &str, pids: &[u32]) {
    for pid in pids {
        let _ = std::process::Command::new("kill")
            .args([sig, &pid.to_string()])
            .output();
    }
}

/// The log line a stop attempt produces. Pulled out of the command so both
/// outcomes are testable without a live `AppHandle` or real processes: the
/// failure branch is precisely the one that must not be
/// reachable-but-untested, since reporting a false success is the original
/// bug (design.md Decision 3).
#[cfg(not(windows))]
fn stop_result_line(survivors: &[u32]) -> String {
    if survivors.is_empty() {
        "Capture engine stopped.".to_string()
    } else {
        format!(
            "Failed to stop the capture engine: {} process(es) still running ({}). \
             Audio capture may still be active.",
            survivors.len(),
            survivors
                .iter()
                .map(|p| p.to_string())
                .collect::<Vec<_>>()
                .join(", ")
        )
    }
}

/// Signals a sidecar's whole process tree and reports what survived.
///
/// SIGINT first so transcriber.py's handler flushes and closes its transcript
/// (a SIGKILL mid-write truncates the last line), then escalate, then
/// re-check -- the return value is what makes "did the stop actually work?"
/// answerable instead of assumed (design.md Decisions 2 and 3).
///
/// Blocking on purpose: tokio is not a direct dependency, and the whole
/// sequence is bounded at ~3s. Called from an async command, so it briefly
/// occupies a runtime worker rather than the UI thread.
#[cfg(not(windows))]
fn terminate_process_tree(pid: u32) -> Vec<u32> {
    let mut targets = descendant_pids(pid);
    // Worker before bootloader: killing the parent first can orphan the
    // child that owns the audio device.
    targets.push(pid);
    signal_pids("-INT", &targets);

    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(3);
    while std::time::Instant::now() < deadline && targets.iter().any(|p| pid_alive(*p)) {
        std::thread::sleep(std::time::Duration::from_millis(100));
    }

    let stubborn: Vec<u32> = targets.iter().copied().filter(|p| pid_alive(*p)).collect();
    if !stubborn.is_empty() {
        signal_pids("-KILL", &stubborn);
        std::thread::sleep(std::time::Duration::from_millis(200));
    }

    // Re-scan as well as re-check: a process may have forked between the
    // original listing and the signal.
    let mut survivors: Vec<u32> = targets.iter().copied().filter(|p| pid_alive(*p)).collect();
    survivors.extend(descendant_pids(pid).into_iter().filter(|p| pid_alive(*p)));
    survivors.sort_unstable();
    survivors.dedup();
    survivors
}

#[tauri::command]
pub async fn stop_live_session(app: AppHandle, state: State<'_, AppState>) -> Result<(), String> {
    // Take the child and release the lock before terminating: a std
    // MutexGuard is not Send, so holding it across the wait would not
    // compile, and holding a lock while waiting seconds for a process to die
    // would be wrong regardless.
    let child = {
        let mut sidecar = state.sidecar.lock().unwrap();
        sidecar.session_active = false;
        sidecar.child.take()
    };
    if let Some(child) = child {
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
            // CREATE_NO_WINDOW: taskkill is a console program, and
            // std::process::Command does not suppress its console the way
            // tauri-plugin-shell does for the sidecar itself -- without this
            // flag a terminal visibly flashes on every stop, which breaks
            // specs/desktop-gui "Launches without a console or terminal
            // window" ("none SHALL appear ... for any process it spawns").
            // Reported from real Windows testing.
            use std::os::windows::process::CommandExt;
            const CREATE_NO_WINDOW: u32 = 0x0800_0000;
            let result = std::process::Command::new("taskkill")
                .args(["/F", "/T", "/PID", &child.pid().to_string()])
                .creation_flags(CREATE_NO_WINDOW)
                .output();
            let line = match result {
                Ok(output) if output.status.success() => {
                    "Capture engine stopped.".to_string()
                }
                Ok(output) => format!(
                    "Failed to stop the capture engine (taskkill exit code {:?}).",
                    output.status.code()
                ),
                Err(e) => format!("Failed to stop the capture engine: {e}"),
            };
            let _ = app.emit("sidecar-log", SidecarLogPayload { line });
        }
        #[cfg(not(windows))]
        {
            let survivors = terminate_process_tree(child.pid());
            let line = stop_result_line(&survivors);
            let _ = app.emit("sidecar-log", SidecarLogPayload { line });
            if !survivors.is_empty() {
                return Err("capture engine did not stop".to_string());
            }
        }
    }
    Ok(())
}

#[tauri::command]
pub async fn start_file_transcription(
    app: AppHandle,
    state: State<'_, AppState>,
    file_path: String,
    format: String,
    task: String,
    model: String,
    language: Option<String>,
) -> Result<(), String> {
    // One engine at a time. A live session's engine keeps the audio device
    // and its own stdout pipe, so starting a file run beside it produced two
    // engines writing into one stream -- live [MIC]/[SYS] lines landed in the
    // file transcript (openspec/changes/fix-live-stop-orphans-engine
    // design.md Decision 4). Refuse rather than silently ending a recording.
    {
        let sidecar = state.sidecar.lock().unwrap();
        if sidecar.session_active || sidecar.child.is_some() {
            return Err(
                "A live session is still running. Stop it before transcribing a file.".to_string(),
            );
        }
        if let Some(existing) = sidecar.file_child.as_ref() {
            #[cfg(not(windows))]
            if pid_alive(existing.pid()) {
                return Err("A file transcription is already running.".to_string());
            }
            #[cfg(windows)]
            let _ = existing;
        }
    }

    // The engine writes its auto-named <stem>_transcript_<stamp>.<format>
    // into its working directory, so running it from the recording's folder
    // saves the transcript next to the recording instead of wherever the app
    // was launched from (openspec/changes/fix-gui-transcript-location).
    let work_dir = std::path::Path::new(&file_path)
        .parent()
        .filter(|dir| !dir.as_os_str().is_empty())
        .map(|dir| dir.to_path_buf());
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
    let mut sidecar_command = app
        .shell()
        .sidecar(SIDECAR_NAME)
        .map_err(|e| e.to_string())?
        .args(args);
    if let Some(dir) = work_dir {
        sidecar_command = sidecar_command.current_dir(dir);
    }
    let (rx, child) = sidecar_command.spawn().map_err(|e| e.to_string())?;
    {
        // Tracked so it can be terminated on quit and so the guard above can
        // see it; still not eligible for crash detection, which belongs to
        // long-lived live sessions.
        let mut sidecar = state.sidecar.lock().unwrap();
        sidecar.file_child = Some(child);
    }
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

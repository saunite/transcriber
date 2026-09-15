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

    /// A stop that takes a few seconds must end by itself, not by SIGKILL:
    /// only then does PyInstaller's bootloader delete its unpacked copy
    /// (openspec/changes/fix-sidecar-temp-leak).
    #[cfg(not(windows))]
    #[test]
    fn a_slow_graceful_exit_is_not_killed() {
        use std::os::unix::process::ExitStatusExt;
        // Like the engine: SIGINT starts a clean shutdown that takes a while.
        let script = "import signal, sys, time\n\
                      signal.signal(signal.SIGINT, lambda *_: (time.sleep(5), sys.exit(0)))\n\
                      print('ready', flush=True)\n\
                      time.sleep(60)\n";
        let Ok(mut engine) = std::process::Command::new("python3")
            .args(["-c", script])
            .stdout(std::process::Stdio::piped())
            .spawn()
        else {
            eprintln!("skipped: python3 is not available");
            return;
        };
        let mut ready = String::new();
        std::io::BufRead::read_line(&mut std::io::BufReader::new(engine.stdout.take().unwrap()), &mut ready).unwrap();
        assert_eq!(ready.trim(), "ready", "the stand-in did not start");
        let started = std::time::Instant::now();
        let survivors = terminate_process_tree(engine.id());
        let took = started.elapsed();
        assert!(survivors.is_empty(), "survivors: {survivors:?}");
        let status = engine.wait().unwrap();
        assert_eq!(status.signal(), None, "the engine was killed ({status:?}) instead of exiting by itself");
        assert_eq!(status.code(), Some(0), "{status:?}");
        assert!(took < std::time::Duration::from_secs(10), "the wait did not end when the engine exited: {took:?}");
    }

    #[test]
    fn only_this_sidecars_dead_copies_are_stale() {
        let dir = scratch_dir("extractions");
        let make = |name: &str, marker: bool| {
            let path = dir.join(name);
            std::fs::create_dir_all(&path).unwrap();
            if marker {
                std::fs::write(path.join(super::EXTRACTION_MARKER), "x").unwrap();
            }
            path
        };
        let dead = make("_MEI000b7664m8XSeA", true); // pid 751204
        make("_MEI00000002abcdef", true); // pid 2, alive
        make("_MEI000b7665unmarked", false); // dead, but not ours
        make("_MEIzzzzzzzznotapid", true); // not a pid
        make("otherfolder", true);
        std::fs::write(dir.join("_MEI00000003file"), "x").unwrap(); // a file, not a folder
        let alive = |pid: u32| pid == 2;
        assert_eq!(stale_extraction_dirs(&dir, alive), vec![dead.clone()]);
        assert_eq!(u32::from_str_radix("000b7664", 16).unwrap(), 751204);
        let _ = std::fs::remove_dir_all(dir);
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

    use super::{
        build_file_args, build_live_session_args, engine_busy, heartbeat_tag, on_terminated, select_model_dir,
        stale_extraction_dirs, strip_extended_length_prefix, RunEnded, SidecarManager,
    };
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
            "/model/dir".to_string(),
            true,
            None,
            false,
            None,
            None,
            None,
            10,
        );
        assert_eq!(args[0], "--live");
        assert_eq!(args.contains(&"--wasapi".to_string()), cfg!(windows), "{args:?}");
        assert_eq!(args.contains(&"--coreaudio-tap".to_string()), cfg!(target_os = "macos"), "{args:?}");
    }

    #[test]
    fn omits_audio_device_when_unset() {
        let args = build_live_session_args(
            "/model/dir".to_string(),
            true,
            None,
            false,
            None,
            None,
            None,
            10,
        );
        assert!(
            !args.contains(&"--audio-device".to_string()),
            "auto-detect (today's default) must stay untouched when no override is given: {args:?}"
        );
    }

    #[test]
    fn passes_audio_device_override_when_set() {
        let args = build_live_session_args(
            "/model/dir".to_string(),
            true,
            None,
            false,
            None,
            None,
            Some(7),
            10,
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
            "/model/dir".to_string(),
            true,
            None,
            false,
            None,
            None,
            None,
            10,
        );
        assert!(
            !args.contains(&"--language".to_string()),
            "auto-detect (empty selection) must omit --language entirely: {args:?}"
        );
    }

    #[test]
    fn passes_language_when_selected() {
        let args = build_live_session_args(
            "/model/dir".to_string(),
            true,
            Some("en".to_string()),
            false,
            None,
            None,
            None,
            10,
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
            "/model/dir".to_string(),
            true,
            None,
            false,
            None,
            Some(stamped.to_string()),
            None,
            10,
        );
        let idx = args
            .iter()
            .position(|a| a == "--output")
            .expect("--output should be present when the frontend supplies a path");
        assert_eq!(args[idx + 1], stamped);
    }

    /// A fresh directory under the system temp dir, removed first if a previous
    /// run left it behind.
    fn scratch_dir(name: &str) -> std::path::PathBuf {
        let dir = std::env::temp_dir().join(format!("transcriber-test-{}-{name}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn no_chosen_folder_selects_the_bundled_model() {
        let bundled = "/bundled/model".to_string();
        assert_eq!(select_model_dir(None, bundled.clone()), Ok((bundled.clone(), true)));
        assert_eq!(select_model_dir(Some(String::new()), bundled.clone()), Ok((bundled, true)));
    }

    #[test]
    fn chosen_folder_with_a_model_is_selected() {
        let dir = scratch_dir("with-model");
        std::fs::write(dir.join("model.bin"), b"").unwrap();
        let chosen = dir.to_string_lossy().into_owned();
        assert_eq!(select_model_dir(Some(chosen.clone()), "/bundled".to_string()), Ok((chosen, false)));
        let _ = std::fs::remove_dir_all(dir);
    }

    #[test]
    fn chosen_folder_without_a_model_is_refused_naming_it() {
        let empty = scratch_dir("no-model");
        let missing = empty.join("gone");
        for dir in [&empty, &missing] {
            let chosen = dir.to_string_lossy().into_owned();
            let err = select_model_dir(Some(chosen.clone()), "/bundled".to_string()).unwrap_err();
            assert!(err.contains(&chosen) && err.contains("model.bin"), "{err}");
        }
        let _ = std::fs::remove_dir_all(empty);
    }

    #[test]
    fn model_size_is_passed_only_for_the_bundled_model() {
        let live = |bundled| build_live_session_args("/m".to_string(), bundled, None, false, None, None, None, 10);
        let file = |bundled| {
            build_file_args("a.wav".into(), "txt".into(), "transcribe".into(), "/m".into(), bundled, None)
        };
        for args in [live(true), file(true)] {
            let i = args.iter().position(|a| a == "--model").expect("--model for the bundled model");
            assert_eq!(args[i + 1], "base");
            assert!(args.windows(2).any(|w| w == ["--model-path", "/m"]), "{args:?}");
        }
        for args in [live(false), file(false)] {
            assert!(!args.contains(&"--model".to_string()), "a chosen folder must not be labelled base: {args:?}");
            assert!(args.windows(2).any(|w| w == ["--model-path", "/m"]), "{args:?}");
        }
    }

    #[test]
    fn one_engine_at_a_time_in_both_directions() {
        let idle = SidecarManager::new();
        assert_eq!(engine_busy(&idle, true), None);
        assert_eq!(engine_busy(&idle, false), None);

        let mut live = SidecarManager::new();
        live.session_active = true;
        assert!(engine_busy(&live, true).unwrap().contains("live session is already running"));
        assert!(engine_busy(&live, false).unwrap().contains("Stop it before transcribing a file"));

        let mut file = SidecarManager::new();
        file.file_running = true;
        assert!(engine_busy(&file, true).unwrap().contains("file transcription is still running"));
        assert!(engine_busy(&file, false).unwrap().contains("file transcription is already running"));
    }

    #[test]
    fn a_live_exit_is_reported_whatever_the_code_unless_the_user_stopped_it() {
        for code in [Some(0), Some(1), None] {
            let mut state = SidecarManager::new();
            state.live_generation = 3;
            state.session_active = true;
            assert_eq!(on_terminated(&mut state, 3, true, code), RunEnded::LiveEnded(code));
            assert!(!state.session_active);
        }
        let mut stopped = SidecarManager::new();
        stopped.live_generation = 3; // stop_live_session already cleared session_active
        assert_eq!(on_terminated(&mut stopped, 3, true, Some(0)), RunEnded::LiveStopped);
    }

    #[test]
    fn a_late_exit_from_an_older_run_changes_nothing() {
        let mut state = SidecarManager::new();
        state.live_generation = 4; // a new session started after run 3 was stopped
        state.session_active = true;
        assert_eq!(on_terminated(&mut state, 3, true, None), RunEnded::Ignored);
        assert!(state.session_active, "the new session must stay active");

        state.file_generation = 2;
        state.file_running = true;
        assert_eq!(on_terminated(&mut state, 1, false, Some(0)), RunEnded::Ignored);
        assert!(state.file_running);
        assert_eq!(on_terminated(&mut state, 2, false, Some(1)), RunEnded::FileDone(false));
        assert!(!state.file_running);
    }

    #[test]
    fn heartbeats_are_neither_transcript_nor_log_lines() {
        assert_eq!(heartbeat_tag("HEARTBEAT MIC"), Some("MIC"));
        assert_eq!(heartbeat_tag("[2026-09-15 10:00:00] [SYS] HEARTBEAT SYS"), None);
        assert!(!super::TRANSCRIPT_LINE_RE.is_match("HEARTBEAT SYS"));
    }

    #[test]
    fn live_args_carry_the_heartbeat_and_the_silence_limit_in_seconds_from_minutes() {
        for (minutes, expected) in [(10, "600"), (0, "0")] {
            let args = build_live_session_args("/m".to_string(), true, None, false, None, None, None, minutes);
            assert!(args.contains(&"--heartbeat".to_string()), "{args:?}");
            assert!(args.windows(2).any(|w| w == ["--silence-timeout", expected]), "{args:?}");
        }
    }

    #[test]
    fn omits_output_when_empty_rather_than_passing_a_blank_path() {
        let args = build_live_session_args(
            "/model/dir".to_string(),
            true,
            None,
            false,
            None,
            Some(String::new()),
            None,
            10,
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
    /// Whether a file run's engine has not exited yet. Set on spawn, cleared
    /// by that run's own exit -- works the same on every OS, unlike a pid
    /// probe (openspec/changes/fix-engine-liveness).
    file_running: bool,
    /// Bumped on every spawn, so an older run's exit -- reported late, after
    /// a quick stop and restart -- can never touch the newer run's state.
    live_generation: u64,
    file_generation: u64,
    /// The current live run's last engine output line (heartbeats excluded),
    /// shown to the user when the session ends by itself.
    last_line: String,
}

impl SidecarManager {
    pub fn new() -> Self {
        Self {
            child: None,
            session_active: false,
            file_child: None,
            file_running: false,
            live_generation: 0,
            file_generation: 0,
            last_line: String::new(),
        }
    }
}

/// Why a new engine may not start, if another one still runs: one engine at a
/// time, in both directions (specs/desktop-gui "On-demand sidecar lifecycle").
fn engine_busy(sidecar: &SidecarManager, starting_live: bool) -> Option<&'static str> {
    let live_running = sidecar.session_active || sidecar.child.is_some();
    match (starting_live, live_running, sidecar.file_running) {
        (true, true, _) => Some("A live session is already running."),
        (true, false, true) => {
            Some("A file transcription is still running. Wait for it to finish before starting a live session.")
        }
        (false, true, _) => Some("A live session is still running. Stop it before transcribing a file."),
        (false, false, true) => Some("A file transcription is already running."),
        (_, false, false) => None,
    }
}

/// What a run's exit means, applied to the shared state. Pure apart from the
/// state it is handed, so every branch is unit-tested.
#[derive(Debug, PartialEq)]
enum RunEnded {
    /// An older run's exit, after a newer run started: nothing changes.
    Ignored,
    /// The live run the user stopped.
    LiveStopped,
    /// The live run ended without the user stopping it, whatever the code.
    LiveEnded(Option<i32>),
    /// A file run finished; true on success.
    FileDone(bool),
}

fn on_terminated(sidecar: &mut SidecarManager, generation: u64, is_live: bool, code: Option<i32>) -> RunEnded {
    if is_live {
        if sidecar.live_generation != generation {
            return RunEnded::Ignored;
        }
        let was_active = sidecar.session_active;
        sidecar.session_active = false;
        sidecar.child = None;
        if was_active {
            RunEnded::LiveEnded(code)
        } else {
            RunEnded::LiveStopped
        }
    } else {
        if sidecar.file_generation != generation {
            return RunEnded::Ignored;
        }
        sidecar.file_running = false;
        sidecar.file_child = None;
        RunEnded::FileDone(code == Some(0))
    }
}

/// `HEARTBEAT <TAG>` lines from `--heartbeat`: a chunk went through the
/// engine, speech or not. Never a transcript line (no brackets).
fn heartbeat_tag(line: &str) -> Option<&str> {
    line.strip_prefix("HEARTBEAT ").map(str::trim)
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
#[serde(rename_all = "camelCase")]
struct LiveSessionEndedPayload {
    code: Option<i32>,
    last_line: String,
}

#[derive(Clone, Serialize)]
struct HeartbeatPayload {
    tag: String,
}

#[derive(Clone, Deserialize, Serialize)]
pub struct DeviceInfo {
    index: u32,
    name: String,
    max_input_channels: u32,
    default_samplerate: f64,
}

/// Reads sidecar stdout/stderr on a background task and turns each line
/// into a `transcript-line`, `sidecar-heartbeat` or `sidecar-log` event --
/// never blocks the UI thread (specs/desktop-gui "UI remains responsive
/// during sidecar activity"). `generation` ties the run's exit to the run it
/// belongs to, so a late exit cannot touch a newer run
/// (openspec/changes/fix-engine-liveness).
fn spawn_sidecar_events(
    app: AppHandle,
    mut rx: tauri::async_runtime::Receiver<CommandEvent>,
    generation: u64,
    is_live: bool,
) {
    tauri::async_runtime::spawn(async move {
        let remember = |app: &AppHandle, line: &str| {
            if !is_live {
                return;
            }
            if let Some(state) = app.try_state::<AppState>() {
                let mut sidecar = state.sidecar.lock().unwrap();
                if sidecar.live_generation == generation {
                    sidecar.last_line = line.to_string();
                }
            }
        };
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let line = String::from_utf8_lossy(&bytes).trim_end().to_string();
                    if let Some(tag) = heartbeat_tag(&line) {
                        let _ = app.emit("sidecar-heartbeat", HeartbeatPayload { tag: tag.to_string() });
                    } else if let Some(captures) = TRANSCRIPT_LINE_RE.captures(&line) {
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
                        remember(&app, &line);
                        let _ = app.emit("transcript-line", payload);
                    } else if !line.trim().is_empty() {
                        remember(&app, &line);
                        let _ = app.emit("sidecar-log", SidecarLogPayload { line });
                    }
                }
                CommandEvent::Stderr(bytes) => {
                    let line = String::from_utf8_lossy(&bytes).trim_end().to_string();
                    if !line.is_empty() {
                        remember(&app, &line);
                        let _ = app.emit("sidecar-log", SidecarLogPayload { line });
                    }
                }
                CommandEvent::Terminated(payload) => {
                    if let Some(state) = app.try_state::<AppState>() {
                        let (ended, last_line) = {
                            let mut sidecar = state.sidecar.lock().unwrap();
                            let ended = on_terminated(&mut sidecar, generation, is_live, payload.code);
                            (ended, std::mem::take(&mut sidecar.last_line))
                        };
                        match ended {
                            // Any exit the user did not ask for is reported,
                            // a success code included: the engine ends by
                            // itself on the silence limit or a lost audio
                            // source (specs/desktop-gui "On-demand sidecar
                            // lifecycle with crash recovery").
                            RunEnded::LiveEnded(code) => {
                                let _ = app.emit(
                                    "live-session-ended",
                                    LiveSessionEndedPayload { code, last_line },
                                );
                            }
                            RunEnded::FileDone(ok) => {
                                let _ = app.emit("file-transcription-complete", ok);
                            }
                            RunEnded::LiveStopped | RunEnded::Ignored => {}
                        }
                    }
                    break;
                }
                _ => {}
            }
        }
    });
}

/// Which model folder a session loads: the bundled one when the user chose
/// none, otherwise the chosen folder -- refused before any engine starts when
/// it holds no model (openspec/changes/choose-model-folder). Returns the folder
/// and whether it is the bundled one.
fn select_model_dir(chosen: Option<String>, bundled: String) -> Result<(String, bool), String> {
    match chosen.filter(|dir| !dir.is_empty()) {
        None => Ok((bundled, true)),
        Some(dir) if std::path::Path::new(&dir).join("model.bin").is_file() => Ok((dir, false)),
        Some(dir) => Err(format!(
            "the model folder {dir} has no model.bin. Choose a faster-whisper model folder under Model, or pick Bundled (base)."
        )),
    }
}

/// `--model base` only names the bundled model; a chosen folder is named by
/// the engine after its own directory, so no size that wasn't loaded appears.
fn model_args(model_dir: String, bundled: bool) -> Vec<String> {
    let mut args = Vec::new();
    if bundled {
        args.extend(["--model".to_string(), "base".to_string()]);
    }
    args.extend(["--model-path".to_string(), model_dir]);
    args
}

/// Builds `start_file_transcription`'s sidecar argument list, testable like
/// the live one below.
fn build_file_args(
    file_path: String,
    format: String,
    task: String,
    model_dir: String,
    bundled: bool,
    language: Option<String>,
) -> Vec<String> {
    let mut args = vec![
        "--file".to_string(), file_path,
        "--format".to_string(), format,
        "--task".to_string(), task,
    ];
    args.extend(model_args(model_dir, bundled));
    if let Some(lang) = language {
        args.push("--language".to_string());
        args.push(lang);
    }
    args
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
    model_dir: String,
    bundled: bool,
    language: Option<String>,
    include_mic: bool,
    mic_device: Option<i32>,
    output_path: Option<String>,
    audio_device: Option<i32>,
    silence_timeout_minutes: u32,
) -> Vec<String> {
    let mut args = vec!["--live".to_string()];
    if cfg!(windows) {
        args.push("--wasapi".to_string());
    } else if cfg!(target_os = "macos") {
        args.push("--coreaudio-tap".to_string());
    }
    args.extend(model_args(model_dir, bundled));
    args.extend([
        // Mirrors win-start-transcription.bat's default invocation:
        // --chunk-duration 10 --actual-time. Not user-configurable (the
        // .bat doesn't expose them either) -- output_path and audio_device
        // below are the pieces of that invocation this UI does let the
        // user override.
        "--chunk-duration".to_string(),
        "10".to_string(),
        "--actual-time".to_string(),
        // The app's own liveness signal and the user's silence setting
        // (openspec/changes/fix-engine-liveness); 0 turns the auto-stop off.
        "--heartbeat".to_string(),
        "--silence-timeout".to_string(),
        silence_timeout_minutes.saturating_mul(60).to_string(),
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
    model_dir: Option<String>,
    language: Option<String>,
    include_mic: bool,
    mic_device: Option<i32>,
    output_path: Option<String>,
    audio_device: Option<i32>,
    silence_timeout_minutes: u32,
) -> Result<(), String> {
    let (model_dir, bundled) = select_model_dir(model_dir, resolve_model_dir(&app)?)?;
    if let Some(reason) = engine_busy(&state.sidecar.lock().unwrap(), true) {
        return Err(reason.to_string());
    }
    let args = build_live_session_args(
        model_dir,
        bundled,
        language,
        include_mic,
        mic_device,
        output_path,
        audio_device,
        silence_timeout_minutes,
    );

    let sidecar_command = app
        .shell()
        .sidecar(SIDECAR_NAME)
        .map_err(|e| e.to_string())?
        .args(args);
    let (rx, child) = sidecar_command.spawn().map_err(|e| e.to_string())?;

    let generation = {
        let mut sidecar = state.sidecar.lock().unwrap();
        sidecar.child = Some(child);
        sidecar.session_active = true;
        sidecar.live_generation += 1;
        sidecar.last_line.clear();
        sidecar.live_generation
    };

    spawn_sidecar_events(app, rx, generation, true);
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

/// The file `transcriber-sidecar.spec` bundles at the root of every unpacked
/// copy, so a `_MEI*` folder is provably this sidecar's before it is removed.
const EXTRACTION_MARKER: &str = "transcriber-sidecar.marker";

/// PyInstaller's one-file bootloader unpacks into `_MEI<pid as 8 hex><random>`
/// and deletes that folder when the engine exits by itself -- but not after a
/// SIGKILL, an app quit mid-session or a crash (openspec/changes/fix-sidecar-temp-leak).
/// Returns this sidecar's leftover copies in `dir`: named `_MEI` + 8 hex
/// digits, holding the marker, and whose bootloader process is not alive.
fn stale_extraction_dirs(dir: &std::path::Path, is_alive: impl Fn(u32) -> bool) -> Vec<std::path::PathBuf> {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return Vec::new();
    };
    entries
        .flatten()
        .filter_map(|entry| {
            let name = entry.file_name().to_string_lossy().into_owned();
            let hex = name.strip_prefix("_MEI")?.get(..8)?;
            let pid = u32::from_str_radix(hex, 16).ok().filter(|_| hex.bytes().all(|b| b.is_ascii_hexdigit()))?;
            let path = entry.path();
            (path.is_dir() && path.join(EXTRACTION_MARKER).is_file() && !is_alive(pid)).then_some(path)
        })
        .collect()
}

/// Whether a leftover copy's bootloader still runs. Uncertainty counts as
/// alive: a copy is only ever removed when its process is provably gone.
fn extraction_owner_alive(pid: u32) -> bool {
    #[cfg(not(windows))]
    {
        pid_alive(pid)
    }
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        match std::process::Command::new("tasklist")
            .args(["/FI", &format!("PID eq {pid}"), "/NH", "/FO", "CSV"])
            .creation_flags(CREATE_NO_WINDOW)
            .output()
        {
            Ok(out) if out.status.success() => String::from_utf8_lossy(&out.stdout).contains(&format!("\"{pid}\"")),
            _ => true,
        }
    }
}

/// Removes this sidecar's leftover unpacked copies from `dir`; run once at app
/// start, off the UI thread. Errors are skipped: a folder that cannot be
/// removed now is tried again next start.
pub fn remove_stale_extractions(dir: &std::path::Path) {
    let removed = stale_extraction_dirs(dir, extraction_owner_alive)
        .into_iter()
        .filter(|path| std::fs::remove_dir_all(path).is_ok())
        .count();
    if removed > 0 {
        eprintln!("Removed {removed} leftover sidecar copies from {}", dir.display());
    }
}

/// How long a stopping engine gets to exit on its own after SIGINT. It
/// finishes the chunk it is transcribing and closes the mic (bounded at 5 s);
/// only an engine that exits by itself lets PyInstaller's bootloader delete
/// its ~350 MB unpacked copy -- SIGKILL leaves it in the temp directory
/// (openspec/changes/fix-sidecar-temp-leak). An engine that exits sooner ends
/// the wait at once.
#[cfg(not(windows))]
const STOP_GRACE: std::time::Duration = std::time::Duration::from_secs(15);

/// Signals a sidecar's whole process tree and reports what survived.
///
/// SIGINT first so transcriber.py's handler flushes and closes its transcript
/// (a SIGKILL mid-write truncates the last line), then escalate, then
/// re-check -- the return value is what makes "did the stop actually work?"
/// answerable instead of assumed (design.md Decisions 2 and 3).
///
/// Blocking on purpose: tokio is not a direct dependency, and the whole
/// sequence is bounded at about STOP_GRACE. Called from an async command, so
/// it occupies a runtime worker rather than the UI thread.
#[cfg(not(windows))]
fn terminate_process_tree(pid: u32) -> Vec<u32> {
    let mut targets = descendant_pids(pid);
    // Worker before bootloader: killing the parent first can orphan the
    // child that owns the audio device.
    targets.push(pid);
    signal_pids("-INT", &targets);

    let deadline = std::time::Instant::now() + STOP_GRACE;
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

/// Ends a sidecar's whole process tree on Windows and describes the result.
///
/// PyInstaller's --onefile bootloader relaunches into a child process on
/// Windows (extracts to a temp dir, then execs into it); killing only the
/// bootloader orphans the actual worker process, which keeps running and
/// holding the audio device -- verified by stopping a live session and finding
/// transcriber-sidecar.exe still alive afterward. taskkill /T kills the whole
/// process tree instead. CREATE_NO_WINDOW: taskkill is a console program, and
/// std::process::Command does not suppress its console the way
/// tauri-plugin-shell does for the sidecar itself -- without this flag a
/// terminal visibly flashes on every stop, which breaks specs/desktop-gui
/// "Launches without a console or terminal window". Reported from real
/// Windows testing.
#[cfg(windows)]
fn taskkill_tree(pid: u32) -> String {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    match std::process::Command::new("taskkill")
        .args(["/F", "/T", "/PID", &pid.to_string()])
        .creation_flags(CREATE_NO_WINDOW)
        .output()
    {
        Ok(output) if output.status.success() => "Capture engine stopped.".to_string(),
        Ok(output) => format!("Failed to stop the capture engine (taskkill exit code {:?}).", output.status.code()),
        Err(e) => format!("Failed to stop the capture engine: {e}"),
    }
}

/// Ends every engine the app started, the way Stop does, when the app exits.
/// tauri-plugin-shell does not end its children on exit: a live engine used to
/// keep capturing, orphaned, after the window was closed mid-session, and its
/// unpacked copy stayed in use (openspec/changes/fix-sidecar-temp-leak). Their
/// exit events see the session already inactive, so nothing is reported.
pub fn stop_all_engines(app: &AppHandle) {
    let Some(state) = app.try_state::<AppState>() else {
        return;
    };
    let children: Vec<CommandChild> = {
        let mut sidecar = state.sidecar.lock().unwrap();
        sidecar.session_active = false;
        sidecar.file_running = false;
        [sidecar.child.take(), sidecar.file_child.take()].into_iter().flatten().collect()
    };
    for child in children {
        #[cfg(not(windows))]
        {
            let survivors = terminate_process_tree(child.pid());
            if !survivors.is_empty() {
                eprintln!("{}", stop_result_line(&survivors));
            }
        }
        #[cfg(windows)]
        {
            let _ = taskkill_tree(child.pid());
        }
    }
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
            let line = taskkill_tree(child.pid());
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
    model_dir: Option<String>,
    language: Option<String>,
) -> Result<(), String> {
    let (model_dir, bundled) = select_model_dir(model_dir, resolve_model_dir(&app)?)?;
    // One engine at a time. A live session's engine keeps the audio device
    // and its own stdout pipe, so starting a file run beside it produced two
    // engines writing into one stream -- live [MIC]/[SYS] lines landed in the
    // file transcript (openspec/changes/fix-live-stop-orphans-engine
    // design.md Decision 4). Refuse rather than silently ending a recording.
    if let Some(reason) = engine_busy(&state.sidecar.lock().unwrap(), false) {
        return Err(reason.to_string());
    }

    // The engine writes its auto-named <stem>_transcript_<stamp>.<format>
    // into its working directory, so running it from the recording's folder
    // saves the transcript next to the recording instead of wherever the app
    // was launched from (openspec/changes/fix-gui-transcript-location).
    let work_dir = std::path::Path::new(&file_path)
        .parent()
        .filter(|dir| !dir.as_os_str().is_empty())
        .map(|dir| dir.to_path_buf());
    let args = build_file_args(file_path, format, task, model_dir, bundled, language);
    let mut sidecar_command = app
        .shell()
        .sidecar(SIDECAR_NAME)
        .map_err(|e| e.to_string())?
        .args(args);
    if let Some(dir) = work_dir {
        sidecar_command = sidecar_command.current_dir(dir);
    }
    let (rx, child) = sidecar_command.spawn().map_err(|e| e.to_string())?;
    let generation = {
        // Tracked so the guard above can see it; its exit is reported as
        // file-transcription-complete, not as a live session ending.
        let mut sidecar = state.sidecar.lock().unwrap();
        sidecar.file_child = Some(child);
        sidecar.file_running = true;
        sidecar.file_generation += 1;
        sidecar.file_generation
    };
    spawn_sidecar_events(app, rx, generation, false);
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

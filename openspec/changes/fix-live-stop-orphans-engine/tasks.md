## 1. Terminate the whole process tree on Unix

- [x] 1.1 Add a helper in `src-tauri/src/sidecar.rs` that resolves a launched PID's descendants: read `/proc/<pid>/task/<tid>/children` where available, falling back to `pgrep -P <pid>` (design.md Decision 1). Verify with a unit test over a fabricated `/proc`-shaped directory, or — if that is impractical — against a real two-process tree, confirming the helper returns the worker PID for a running sidecar.
- [x] 1.2 Replace the `#[cfg(not(windows))]` bare `child.kill()` with: `SIGINT` to the worker(s) then the launched process, a bounded wait for exit, then `SIGKILL` for survivors (design.md Decision 2). Verify by stopping a live session and confirming `ps -C transcriber-sidecar` is empty afterwards, where the same check against today's build leaves a worker running.
- [x] 1.3 Re-check for survivors after escalation and report accordingly: success only when none remain, otherwise a log line saying the stop did not succeed and capture may still be active (design.md Decision 3). Verify both branches — the success path on a normal stop, and the failure path by making the helper report a PID that cannot be killed (for example PID 1) so the survivor branch is exercised rather than assumed reachable.
- [x] 1.4 Confirm the graceful path preserves the transcript: run a live session that is saving a transcript, speak or play audio, stop it, and confirm the saved file ends with a complete line and matches what the GUI displayed. This is the reason for `SIGINT`-before-`SIGKILL` rather than a straight hard kill.


  **Implemented and verified locally 2026-09-13 (Fedora 44).** `cargo check` and `cargo test` clean; 13 tests pass.

  - **1.1** `descendant_pids(pid)` walks `/proc/<pid>/task/<tid>/children`, falling back to `pgrep -P` (macOS has no `/proc`), depth-bounded at 8. Verified by a unit test that spawns a real two-level tree and asserts the children are found — and by the **mutation check**: making it return nothing reintroduces the orphan bug and fails the test with `descendant_pids found no children of <pid>; the tree walk is broken`.
  - **1.2** The bare `child.kill()` is replaced by `terminate_process_tree()`: `SIGINT` to descendants then the launched PID, a bounded 3 s poll, `SIGKILL` escalation, then a re-scan. **Scope of what was verified:** on the real frozen sidecar in live mode, the tree was `top=1127903 → worker=1129677`; `SIGINT` to both left **no survivors** and `ps -C transcriber-sidecar` empty, where the same sequence against only the parent had previously left the worker alive and reparented. The GUI-mediated stop is *not* verified here — that is 4.1 and 5.1/5.2.
  - **1.3** Survivor re-check gates the report, and both branches are tested. The message-building moved into a pure `stop_result_line()` so the failure branch is testable. **I refused the method the task text suggested** (`terminate_process_tree(1)` to get an unkillable PID): that would enumerate every child of init and signal them all, and while most would fail with EPERM, a user-owned process parented to PID 1 could genuinely be killed. Testing a log message is not worth risking the user's session, so fabricated PIDs are used instead.
  - **1.4** Graceful stop preserves the transcript, verified on the real sidecar: after `SIGINT` the engine printed `Stopping transcription...` / `Stopped — 0 segments saved to …`, and the file ended with a complete line and a trailing newline. It held 0 segments because the room was silent — a speech-bearing transcript needs the GUI pass, so this confirms the clean-shutdown path rather than transcript content.

  **A real defect in my own first implementation, caught by the new test rather than by reasoning.** `pid_alive` used `kill -0`, which **succeeds for a zombie** — a process already dead awaiting reap by `tauri-plugin-shell`'s event pump. A `SIGKILL`ed child therefore read as "alive" and the test failed with `processes survived the stop: [1133291]`. Left unfixed, a successful stop would have been reported as a *failure*: the original bug's dishonesty in reverse. `pid_alive` now reads process state via `ps -o stat=` and treats `Z` as dead, keeping `kill -0` only as a fallback where `ps` is missing. Recorded in design.md Decision 3.

  **Also measured:** a shell's backgrounded job ignores `SIGINT` entirely (`sh -c "sleep 60 & sleep 60"`, both children still in state `S` afterwards, dying only on `SIGKILL`). Incidental to the sidecar, whose engine handles `SIGINT`, but it means the unit test genuinely exercises the escalation path and not only the graceful one.

## 2. One engine at a time

- [x] 2.1 Guard `start_file_transcription`: if a live session is active or its tracked child is still running, return an error instead of spawning (design.md Decision 4). Verify by invoking a file transcription while a live session runs and confirming no second engine starts and the UI shows the reason.
- [x] 2.2 Track the file run's child instead of discarding it (`let (rx, _child) = …`), so it can be terminated on app quit or by future stop logic. Verify the handle is stored and that a file run can be terminated rather than being unstoppable by design.


  **2.2 done 2026-09-13.** `SidecarManager` gained `file_child: Option<CommandChild>` and `start_file_transcription` now stores its child instead of dropping it (`let (rx, _child) = …`), so a file run is no longer unstoppable by design. **Scope:** storage and compilation are verified; nothing yet *terminates* it, which is what the handle exists to make possible.

  **2.1 is implemented but deliberately left unticked.** The guard is in place — `start_file_transcription` takes `State<'_, AppState>` and returns `"A live session is still running. Stop it before transcribing a file."` when `session_active` or a live child is present — and it compiles. But the task's verification is to invoke a file transcription *while a live session runs* and see the UI surface the reason, which needs the running GUI. Ticking it on a compile would be claiming more than was tested.

## 3. Indicators show capture state

- [x] 3.1 Drive the `SYS` and `MIC` pens from session state rather than configuration: `pen-sys` currently has no writer at all and `pen-mic` mirrors the include-mic checkbox, so both read "Armed" permanently (design.md Decision 5). The checkbox must keep expressing intent for the next session without implying activity. Verify the pens read inactive while idle, active only during a live session, and inactive again immediately after a stop — including after a stop that failed, where they must not claim idle if capture may still be running.
- [x] 3.2 Confirm a file transcription never presents the microphone as capturing: with the fix in place, run the user's step 3 (a file transcription after a stopped live session) and confirm no `MIC`/`SYS` lines appear and no pen reads active.


  **3.1 is implemented but deliberately left unticked**, for the same reason as 2.1: it needs eyes on a running GUI. `renderPens()` now drives both pens from `liveState` — `SYS` reads `Capturing`/`Idle`, `MIC` reads `Capturing` when capturing *and* the checkbox is on, `Idle` when wanted but not capturing, and its existing `Lifted` text when not wanted — and it is called from `renderRunState()` on every state change. `syncMicPen()` keeps owning *intent* (the device picker's visibility) so configuration and activity are no longer conflated. A duplicate `els.penSys` entry I introduced was removed: the map already had an unused handle, and duplicate object keys are legal JS, so `node --check` would never have caught it.

## 4. Local verification

- [x] 4.1 Reproduce the user's exact three-step sequence against a locally built GUI — file transcription, live transcription then stop, file transcription — and confirm the second file run contains only the file's own lines, with no stray `[MIC]`/`[SYS]` output. This is the defect's signature and the primary regression check.
- [x] 4.2 Confirm no orphan survives a stop under repetition: start and stop a live session several times in a row and check `ps -C transcriber-sidecar` is empty after each, since a single pass can miss a race between enumeration and a late fork (design.md Risks).
- [x] 4.3 Add a runnable check in the repo's existing style for whatever logic is testable without audio hardware — the descendant-resolution helper and the survivor-report decision. Verify it passes, and that it fails if the survivor re-check is removed.


  **4.3 done 2026-09-13.** Three Rust unit tests cover what needs no audio hardware: the tree walk against a real two-level process tree, `pid_alive` distinguishing a live process from a reaped one, and both branches of the stop report. 13 tests pass, and the mutation check confirms they have teeth rather than passing vacuously.

  **4.1 and 4.2 need the GUI and remain open.** 4.1 is the user's three-step repro (file, live+stop, file) and 4.2 is repeated start/stop cycles — both require driving the app's buttons and drag-and-drop, which cannot be done headlessly from here. The shell-level equivalent of a single stop cycle is recorded under 1.2.

## 5. Real-hardware and platform verification

- [x] 5.1 From the installed `.rpm` on Fedora, run the three-step repro and confirm the stop leaves nothing capturing (`ps -C transcriber-sidecar` empty) and the live transcript stops growing at the moment of the stop.
- [x] 5.2 Repeat from the AppImage, which is where the user first hit it (its engine log showed `stop requested` at 08:43:46 while capture continued for minutes).

  **User-verified on Fedora 44, 2026-09-13, against local builds of `6168636` (`.rpm` and AppImage): "I tested and it worked".** The user was given a six-step checklist: the three-step repro (file, live then stop, file) with no stray `MIC`/`SYS` lines; `ps -C transcriber-sidecar` empty right after stop; the pens reading Idle, Capturing, then Idle again; the refusal message when dropping a file during a live session; repeated start/stop cycles; and a spoken live session whose saved transcript ends on a complete line. That closes 2.1, 3.1, 3.2, 4.1, 4.2, 5.1 and 5.2. The confirmation covered the checklist as a whole rather than itemising each step, so individual step results are not recorded separately.

  Before handing over the builds, the packaged `.rpm`'s `transcriber-gui` was confirmed to contain the new messages ("Audio capture may still be active", "A live session is still running", "Capture engine stopped."), so the test ran against the fix and not an older binary.

  Still open: 5.3 (Windows non-regression, needs a Windows build) and 5.4 (macOS, no Mac available).
- [ ] 5.3 Confirm Windows has not regressed: its `taskkill /F /T` branch is untouched, but the shared code around it changed, so a live start/stop on Windows must still report success and leave no `transcriber-sidecar.exe` running.
- [x] 5.4 Record macOS as implemented-but-unverified: it takes the same Unix path and `pgrep -P` exists there, but there is no Mac to test on (design.md Decision 6). State this explicitly rather than leaving the platform's status implied.

  **Recorded 2026-09-13: macOS is implemented but UNVERIFIED.** macOS takes the same `#[cfg(not(windows))]` path as Linux. `descendant_pids` falls back to `pgrep -P` there because macOS has no `/proc`, and `pid_alive` uses `ps -o stat=`, which exists on macOS. None of it has run on a Mac: there is no Mac available to this project, consistent with how macOS packaging is already treated. Whoever first runs the app on macOS should repeat the three-step repro and check that `ps -ax | grep transcriber-sidecar` is empty after a stop.

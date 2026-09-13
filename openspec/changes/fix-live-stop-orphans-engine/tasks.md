## 1. Terminate the whole process tree on Unix

- [ ] 1.1 Add a helper in `src-tauri/src/sidecar.rs` that resolves a launched PID's descendants: read `/proc/<pid>/task/<tid>/children` where available, falling back to `pgrep -P <pid>` (design.md Decision 1). Verify with a unit test over a fabricated `/proc`-shaped directory, or — if that is impractical — against a real two-process tree, confirming the helper returns the worker PID for a running sidecar.
- [ ] 1.2 Replace the `#[cfg(not(windows))]` bare `child.kill()` with: `SIGINT` to the worker(s) then the launched process, a bounded wait for exit, then `SIGKILL` for survivors (design.md Decision 2). Verify by stopping a live session and confirming `ps -C transcriber-sidecar` is empty afterwards, where the same check against today's build leaves a worker running.
- [ ] 1.3 Re-check for survivors after escalation and report accordingly: success only when none remain, otherwise a log line saying the stop did not succeed and capture may still be active (design.md Decision 3). Verify both branches — the success path on a normal stop, and the failure path by making the helper report a PID that cannot be killed (for example PID 1) so the survivor branch is exercised rather than assumed reachable.
- [ ] 1.4 Confirm the graceful path preserves the transcript: run a live session that is saving a transcript, speak or play audio, stop it, and confirm the saved file ends with a complete line and matches what the GUI displayed. This is the reason for `SIGINT`-before-`SIGKILL` rather than a straight hard kill.

## 2. One engine at a time

- [ ] 2.1 Guard `start_file_transcription`: if a live session is active or its tracked child is still running, return an error instead of spawning (design.md Decision 4). Verify by invoking a file transcription while a live session runs and confirming no second engine starts and the UI shows the reason.
- [ ] 2.2 Track the file run's child instead of discarding it (`let (rx, _child) = …`), so it can be terminated on app quit or by future stop logic. Verify the handle is stored and that a file run can be terminated rather than being unstoppable by design.

## 3. Indicators show capture state

- [ ] 3.1 Drive the `SYS` and `MIC` pens from session state rather than configuration: `pen-sys` currently has no writer at all and `pen-mic` mirrors the include-mic checkbox, so both read "Armed" permanently (design.md Decision 5). The checkbox must keep expressing intent for the next session without implying activity. Verify the pens read inactive while idle, active only during a live session, and inactive again immediately after a stop — including after a stop that failed, where they must not claim idle if capture may still be running.
- [ ] 3.2 Confirm a file transcription never presents the microphone as capturing: with the fix in place, run the user's step 3 (a file transcription after a stopped live session) and confirm no `MIC`/`SYS` lines appear and no pen reads active.

## 4. Local verification

- [ ] 4.1 Reproduce the user's exact three-step sequence against a locally built GUI — file transcription, live transcription then stop, file transcription — and confirm the second file run contains only the file's own lines, with no stray `[MIC]`/`[SYS]` output. This is the defect's signature and the primary regression check.
- [ ] 4.2 Confirm no orphan survives a stop under repetition: start and stop a live session several times in a row and check `ps -C transcriber-sidecar` is empty after each, since a single pass can miss a race between enumeration and a late fork (design.md Risks).
- [ ] 4.3 Add a runnable check in the repo's existing style for whatever logic is testable without audio hardware — the descendant-resolution helper and the survivor-report decision. Verify it passes, and that it fails if the survivor re-check is removed.

## 5. Real-hardware and platform verification

- [ ] 5.1 From the installed `.rpm` on Fedora, run the three-step repro and confirm the stop leaves nothing capturing (`ps -C transcriber-sidecar` empty) and the live transcript stops growing at the moment of the stop.
- [ ] 5.2 Repeat from the AppImage, which is where the user first hit it (its engine log showed `stop requested` at 08:43:46 while capture continued for minutes).
- [ ] 5.3 Confirm Windows has not regressed: its `taskkill /F /T` branch is untouched, but the shared code around it changed, so a live start/stop on Windows must still report success and leave no `transcriber-sidecar.exe` running.
- [ ] 5.4 Record macOS as implemented-but-unverified: it takes the same Unix path and `pgrep -P` exists there, but there is no Mac to test on (design.md Decision 6). State this explicitly rather than leaving the platform's status implied.

## 1. Move the existing material

- [x] 1.1 Create `docs/building.md` from today's README L94–L225: the "Building it yourself" intro (toolchains, `CARGO_TARGET_DIR`), "Updating the icon", "Linux build (WSL or native Linux)", "Windows build (from WSL)" and "Releasing". Keep the commands and the hard-won notes verbatim (the `NO_STRIP=1` explanation, the venv-not-system-Python warning, the `/mnt/c` warning, the `-compose over` note in the icon command). Fix the dead `openspec/changes/drop-ffmpeg-dependency/` link (now `openspec/changes/archive/2026-09-08-drop-ffmpeg-dependency/`).

  Verify `docs/building.md` carries every command block from that range and that the range is gone from `README.md`.

  **Done 2026-09-16.** 136 lines. The section heading became the file title, `####` headings became `##`, and the body is otherwise verbatim, including the `/mnt/c`, `NO_STRIP=1`, venv-not-system-Python and `-compose over` notes. The ffmpeg link now points at `openspec/changes/archive/2026-09-08-drop-ffmpeg-dependency/`. Fence count matches the source range exactly (20). The range left `README.md` in task 2.2.

- [x] 1.2 Create `docs/user-guide.md` from today's README L275–L517 and L533–L572: "Requirements", "Usage" (file, real-time capture, launchers, advanced options, complete options), "Setup for Real-time Audio Capture" (Windows, Linux, macOS), "Performance Tips", "Troubleshooting" and "Examples". Keep the `--help` output block and the per-platform setup verbatim.

  Verify the option tables and every fenced command block survive, and that the ranges are gone from `README.md`.

  **Done 2026-09-16.** 295 lines. Heading levels are unchanged under a new `# User guide` title, so the sections read as they did. All 30 fenced blocks survive, including the full `--help` output; the source had no Markdown tables in these ranges.

  One addition beyond the task text: task 2.2 moved three app-behaviour paragraphs out of the README's install section into a new "The desktop app" section here (choosing a model folder, what happens when a session stops by itself, and the engine's temporary unpacking). They describe using the app, not installing it.

- [x] 1.3 Create `CONTRIBUTING.md` with "Running the tests" moved from README L226–L274 (the suite table, the `TRANSCRIBER_TEST_SPEECH` note, the e2e prerequisites, the frozen-engine note), under a section that also says how to verify a change.

  Verify the suite table and all three command blocks survive, and that the range is gone from `README.md`.

  **Done 2026-09-16.** The tests section is moved verbatim under "Running the tests": all 7 table rows and all 10 fences match the source range. A closing line was added saying the suite passes for every change, and that a skipped suite is reported rather than counted as a clean run.

## 2. Write the new material

- [x] 2.1 Write the rest of `CONTRIBUTING.md` (new text), covering:
  - **The OpenSpec loop:** `openspec/specs/` is the contract and `openspec/changes/` is work in flight; a change is proposed (proposal, spec deltas, tasks), applied, then archived with its deltas merged into the specs; `openspec validate --strict`; `openspec/backlog.md` holds parked work.
  - **Tests:** every change lands with the suite passing; a fix starts with a test that fails first.
  - **Desktop interface changes:** they go through the Impeccable design pass with an independent finish review, and `DESIGN.md` is updated.
  - **Branches:** work lands on `dev`; `main` is only fast-forwarded to it.

  Verify it reads for someone with no prior knowledge of this repo, and names no house rule beyond the four points above.

  **Done 2026-09-16.** 109 lines with four sections: "How changes are made" (specs as the contract, changes in flight, archive and backlog, the propose/implement/archive loop, `openspec validate --strict`, and the two habits: test first, say what you verified), "Running the tests", "Changing the desktop interface" (the design pass, screenshots light and dark at both sizes, independent review, `DESIGN.md`), and "Branches" (`dev`, with `main` only fast-forwarded). It opens by saying what the project is and links to the user guide and the build doc. No other house rule is named.

- [x] 2.2 Rewrite `README.md` short (target: about 120 lines), in this order: icon and one-paragraph description; what it does (trimmed features); **Install** (desktop app per platform, from today's "Download and run", keeping the macOS testers call and the unsigned-binary notes); **Run it** (the app in a few steps, then the CLI in a few lines); **Where next** (links to `docs/user-guide.md`, `CONTRIBUTING.md`, `docs/building.md`); **License** (kept verbatim: the `licensing` capability names `LICENSE` and `README`).

  It leads with the desktop app and drops the "(in development)" framing. Fix the dead `openspec/changes/add-tauri-gui/` link: either point at `openspec/changes/archive/2026-09-02-add-tauri-gui/` or drop the sentence.

  Verify with a read-through that nothing in the four documents is duplicated, and that `README.md` is under 150 lines.

  **Done 2026-09-16.** 122 lines: title and one-paragraph description, four bullets on what it does, a line on where live capture works, **Install** (the release forms, then Linux, Windows, macOS and the CLI archive, with the testers call and the unsigned-binary notes kept), **Run it** (the app in a sentence, then three CLI commands), **Where next** (three links), and the License section verbatim. The "(in development)" framing is gone, and the dead `openspec/changes/add-tauri-gui/` sentence was dropped rather than repointed: the app is no longer "in progress under `src-tauri/`", so the sentence had nothing to say. The stale "(see [macOS](#macos) below)" cross-reference now points at `docs/user-guide.md#macos`.

- [ ] 2.3 Run the `no-ai-slop` skill over `README.md`, `CONTRIBUTING.md`, `docs/user-guide.md` and `docs/building.md`, in detect mode first, then apply the edits worth making. Record under this task which patterns it named and what changed.

  Verify each document still carries every command block and table it had before the pass.

## 3. Repoint everything that names a README section

- [ ] 3.1 Update the six references:
  - `build_portable.py:257` ("see README.md's WSL build section or 'cargo tauri build'");
  - `tests/test_e2e_linux.py:50` ("README's WSL build notes") and `:89` ("the README's sidecar steps");
  - `.github/workflows/release.yml:42` ("README 'Releasing' licensing check") and `:155` ("README Linux build notes");
  - `openspec/backlog.md`'s release item ("per README 'Releasing'", "README 'Releasing' step 4").

  Verify `grep -rn "README" build_portable.py tests/test_e2e_linux.py .github/workflows/release.yml openspec/backlog.md` names only documents that exist.

- [ ] 3.2 Check every link and anchor. Collect the Markdown links and `#anchor` references in the four documents, and verify each anchor exists in its own file and each relative path exists on disk (for example the features list's `[macOS](#macos)`, which now crosses a file boundary). Fix what broke.

  Verify by listing the checked links and their targets under this task.

- [ ] 3.3 Remove the backlog's "Minor" dead-link item, now that both links are fixed. Verify it no longer appears in `openspec/backlog.md`.

## 4. Verification

- [ ] 4.1 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub, and verify it exits 0. Nothing here changes behaviour, so this is a regression check on the touched Python and workflow files.

- [ ] 4.2 **Review, by the user:** read the four documents and confirm the front page is what you want a new visitor to land on, and that nothing you rely on was lost in the move.

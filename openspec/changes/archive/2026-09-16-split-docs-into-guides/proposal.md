## Why

`README.md` is 572 lines and serves four audiences at once. About 181 of those lines (L94–L274: toolchains, icon export, the Linux and Windows builds, releasing, running the tests) only matter to someone building the project, and they sit between "Download and run" and "Requirements", where a new user hits them on the way to the usage examples. The reference material (every flag, per-platform capture setup, troubleshooting) is another ~260 lines below that.

Meanwhile nothing documents **how work happens here**: the OpenSpec loop, that GUI changes go through an Impeccable design pass, that `main` only fast-forwards, or what a change needs before it's done. That's only in tooling config and habit, so an outside contributor can't find it.

Decided with the user on 2026-09-16: split into four documents, keep the front page short, and lead with the desktop app rather than the CLI.

## What Changes

- **`README.md` (front page, kept short):** what the tool is, the desktop app first and the CLI second, how to install and run each, where to go next, and the License section, which stays here because the `licensing` capability names `LICENSE` and `README`. The "Desktop GUI (in development)" framing goes: it's built, tested and waiting on a release.
- **`docs/user-guide.md` (new):** requirements, file and live transcription, launchers, advanced and complete options, per-platform capture setup, performance tips, troubleshooting and examples.
- **`CONTRIBUTING.md` (new, mostly new text):** the OpenSpec loop (propose, apply, archive; specs are the contract), running the tests (moved from the README), the Impeccable design pass for GUI changes, and that work lands on `dev` with `main` only fast-forwarded.
- **`docs/building.md` (new):** toolchains and the cargo target directory, updating the icon, the Linux and Windows builds, releasing.
- **Prose:** every document's text goes through the `no-ai-slop` skill, since this rewrites the front page rather than only moving blocks.
- **Fixed on the way:** two dead links in today's README, to `openspec/changes/add-tauri-gui/` (L18) and `openspec/changes/drop-ffmpeg-dependency/` (L200); both were archived. The second is the backlog's "Minor" item.
- **Repointed:** the six places that name README sections — `build_portable.py:257`, `tests/test_e2e_linux.py:50` and `:89`, `.github/workflows/release.yml:42` and `:155`, and `openspec/backlog.md`'s "per README 'Releasing'".
- **Not in this change:** no behaviour, code or GUI changes; `DESIGN.md`, `PRODUCT.md`, `LICENSE` and `THIRD-PARTY-LICENSES.txt` stay where they are.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `documentation`, "Project documentation mirrors supported behavior": documentation is four documents with defined owners — a short front page, a user reference, contributor workflow, and build and release steps — and the requirement to stay in step with behaviour applies to whichever document owns the subject, rather than to the README alone.

## Impact

- **`README.md`:** rewritten short; most content moves out.
- **New:** `CONTRIBUTING.md`, `docs/user-guide.md`, `docs/building.md`.
- **`build_portable.py`, `tests/test_e2e_linux.py`, `.github/workflows/release.yml`, `openspec/backlog.md`:** the README references above, plus removing the backlog's dead-link item once fixed.
- **Links:** in-page anchors that cross the new file boundaries (for example the features list's `[macOS](#macos)`) need repointing.
- **No tests change.** Nothing automated asserts on the README's structure; `run_tests.py` is unaffected.

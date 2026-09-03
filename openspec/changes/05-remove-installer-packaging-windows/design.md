## Context

See proposal.md - Why, and `openspec/changes/remove-installer-packaging/design.md` for the original packaging decisions (single-artifact-per-OS rationale, why Windows gets a zip not an installer). This change adds no new decisions of its own — it completes that change's Windows-only verification, now against an artifact built via `03-add-wsl-windows-build` instead of `docker/build.ps1`.

## Goals / Non-Goals

**Goals:**
- Complete `remove-installer-packaging`'s open Windows tasks (2.6, 4.2, 4.3, 5.1, Windows portion of 5.4) for real, on Windows hardware.
- Leave a clear trail in `remove-installer-packaging/tasks.md` showing these tasks moved here, so that change can archive its general/Linux scope.

**Non-Goals:**
- Any new packaging decision — `remove-installer-packaging/design.md` already made them.
- macOS verification (`06`).

## Decisions

**No new technical decisions; this change inherits `remove-installer-packaging`'s design as-is.** The only procedural choice here is annotating the source change's tasks rather than deleting the verification history already recorded there for the Windows-adjacent tasks that were partially verified (2.6, 5.1) — that context stays valuable.

## Risks / Trade-offs

- [Verification surfaces a real Windows-only bug not anticipated by `remove-installer-packaging/design.md`] → Mitigation: fix it here and record it in this change's own tasks.md, same pattern that change used for its own findings (e.g. task 3.5's upload-glob fix).

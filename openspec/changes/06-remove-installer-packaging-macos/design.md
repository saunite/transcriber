## Context

See proposal.md - Why, and `openspec/changes/remove-installer-packaging/design.md` for the original packaging decisions. This change adds no new decisions — it holds macOS-only verification scope split out of that change, parked pending hardware/CI availability.

## Goals / Non-Goals

**Goals:**
- Preserve the macOS verification scope (tasks 4.5, 5.3, 5.4-macos) as a tracked, explicitly-parked change rather than losing it or leaving it stuck unarchivable inside `remove-installer-packaging`.

**Non-Goals:**
- Actually performing the verification now — no macOS hardware is available.
- Deciding how macOS builds will work once `04-remove-ci-and-container-builds` removes the `macos-latest` CI job (its only current build path). That is a real open question, deliberately deferred.

## Decisions

**Park rather than delete.** `add-macos-capture` (21/27 tasks, all 6 open ones needing macOS hardware) and real code (`macos_capture.py`, `macos/`, `test_macos_capture.py`) already exist in the tree; dropping this scope would strand that work with no path back. Parking costs nothing and keeps the scope visible.

## Open Questions

- ~~[Once CI's `macos-latest` job is gone (`04`), what replaces it as a macOS build path?]~~ **Resolved: a developer-owned Mac, building locally.** `Transcriber.app` was built end to end this way with no CI involvement; the exact toolchain and step order is recorded in tasks.md 3.1. Caveat worth carrying forward: Command Line Tools alone cannot produce a universal (arm64+x86_64) binary — that needs full Xcode.app — so this path yields a single-architecture app matching whichever Mac builds it.

## Risks / Trade-offs

- [This change sits open indefinitely with no forcing function to revisit it] → Mitigation: none automated; revisit when macOS hardware/CI becomes available again, same as `add-macos-capture`'s own already-parked verification tasks.

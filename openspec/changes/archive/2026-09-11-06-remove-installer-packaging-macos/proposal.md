## Why

Same rationale as `05-remove-installer-packaging-windows`: `remove-installer-packaging`'s macOS-only outstanding verification (tasks 4.5, 5.3, and the macOS portion of 5.4) is split out per `01-adopt-platform-split-requirements` so the parent change can archive without waiting on a platform that currently has no available hardware or CI runner. Development is explicitly focused on Windows and Linux for now (user directive) — this change is created to hold the outstanding scope and make that parking explicit, not to be worked immediately.

## What Changes

- Take ownership of `remove-installer-packaging` tasks 4.5, 5.3, and the macOS portion of 5.4.
- `remove-installer-packaging`'s own `tasks.md` is annotated marking these tasks as superseded/moved here, same as `05`.
- **This change is parked.** It stays open and unworked until macOS hardware (or an equivalent verification path) is available again. `04-remove-ci-and-container-builds` removes `macos-latest` from CI along with the rest of the workflow, which was the only mechanism that could produce a macOS artifact at all — so this change also has no build path until that gap is separately addressed (out of scope here; noted as an open question).

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
(none — same as `05`: verifies an already-authored `desktop-gui` delta, does not change it)

This change sets `skip_specs: true` in `.openspec.yaml`: it is pure verification of already-specified behavior, not a behavior change.

## Impact

- **Affected**: `openspec/changes/remove-installer-packaging/tasks.md` (annotation only).
- **Blocked on**: macOS hardware or CI availability — not scheduled, tracked here so the scope isn't lost.

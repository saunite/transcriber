## Why

The project is moving all development onto Linux/WSL, which starts a run of build-migration work (removing CI, removing the Docker cross-compile container, adding native WSL build paths) that inherently differs between Windows and Linux. Recent in-flight changes already show the cost of not separating platform-specific work: `remove-installer-packaging` (21/28 tasks), `drop-ffmpeg-dependency` (14/15), and `add-macos-capture` (21/27) each sit unarchived because a handful of platform-only verification tasks block a change whose general work is otherwise done. Codifying a change-level platform split now — before the build-migration changes are created — lets each platform's work land and archive independently.

## What Changes

- Add a `project-workflow` requirement: when a piece of work needs genuinely different implementation per platform, it is split into separate OpenSpec changes — one change for the platform-agnostic part, and one additional change per platform that needs distinct implementation. A change that merely gets verified on multiple platforms without different implementation does not need to split.
- Add a `project-workflow` requirement: when multiple related changes are created together, their directory names carry a two-digit application-order prefix (e.g. `01-foo`, `02-foo-linux`, `03-foo-windows`), so sequencing is visible from the change list alone.
- Wire both rules into `openspec/config.yaml`'s `rules:` block (proposal, design, specs, tasks) so every generated artifact's instructions include them, matching how the existing ponytail rule is surfaced.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `project-workflow`: adds the platform-split-by-change requirement and the ordered-numbering-for-related-changes requirement, alongside the existing ponytail-optimization and accurate-context requirements.

## Impact

- `openspec/specs/project-workflow/spec.md` — two new requirements.
- `openspec/config.yaml` — `rules:` block gains the two new rules under `proposal`, `design`, `specs`, `tasks`.
- No application code changes. This change only establishes the convention; it does not itself re-slice the in-flight changes or perform the CI/Docker removal (that follow-up work, changes `02` onward, will apply this convention once it exists).

## Context

See proposal.md - Why. This is a pure workflow-convention change: two new requirements in `project-workflow` plus their mirror in `openspec/config.yaml`'s `rules:` block, matching the existing pattern used for the ponytail rule (`openspec/config.yaml` context/rules, `openspec/specs/project-workflow/spec.md:5-16`).

## Goals / Non-Goals

**Goals:**
- State the platform-split-by-change rule precisely enough to apply it consistently to the upcoming build-migration changes (`02` onward).
- Surface the rule automatically in every generated artifact's instructions, the same way the ponytail rule already is.

**Non-Goals:**
- Re-slicing the existing in-flight changes (`remove-installer-packaging`, `drop-ffmpeg-dependency`, `add-macos-capture`) - a separate follow-up.
- Defining the actual CI/Docker-removal or WSL-build changes - separate follow-ups (`02`-`06`).

## Decisions

**Split at the change level, not the requirement level.** OpenSpec's archive gate is the change, not the individual requirement - a change mixing general + Windows + Linux work can't archive until every platform's tasks are verified, which is what currently blocks the three in-flight changes named in proposal.md. Splitting at the change level lets a platform-agnostic (or single-platform) portion archive independently of a platform that's blocked or unavailable (e.g. no Mac hardware).

Alternative considered: split only at the requirement level within one change (separate `### Requirement: X on Windows` / `### Requirement: X on Linux` blocks, one change). Rejected - it documents the distinction but doesn't fix the archive-blocking problem, since the whole change still waits on every platform.

**Trigger is "different implementation required," not "touches multiple platforms."** A change that happens to get verified on two platforms in one sitting, with no implementation divergence, does not need to split. Splitting is for genuine per-platform branches (e.g. WASAPI vs PulseAudio/PipeWire, or a Windows-only build step).

**Numbering convention: two-digit prefix in application order.** When related changes are created together, name them `NN-name` (`01-foo`, `02-foo-linux`, `03-foo-windows`) so sequencing is visible from `openspec/changes/` listing alone, without opening each proposal. Applies only when changes are created as a related batch; a standalone change needs no prefix.

**Wire into `openspec/config.yaml` alongside `project-workflow`.** The spec states the rule; the config's `rules:` block enforces it at authoring time by injecting it into every artifact's generated instructions - same split of responsibility the ponytail rule already uses.

## Risks / Trade-offs

- [More changes to track for genuinely small platform-specific features] → Mitigation: the trigger is scoped to "different implementation required," not every multi-platform touch, so small changes verified everywhere at once stay as one change.
- [Numbering can drift if a change is inserted later into an already-numbered batch] → Mitigation: numbering is a visibility aid, not an enforced ordering mechanism; renumbering an existing batch is a rename, not a spec violation.

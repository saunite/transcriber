## Why

The project's `openspec/config.yaml` is still a scaffold: it carries no description of this application, and nothing guarantees that changes are reviewed for over-engineering. Every change should be run through the ponytail skill so the codebase stays lean; without an explicit rule, the constraint is easy to forget.

## What Changes

- Fill `context` in `openspec/config.yaml` with a short description of the application (what it is, its tech stack, conventions) so artifact instructions are written with accurate project background.
- Add a custom rule to every artifact in the `rules:` section of `openspec/config.yaml`:
  - ALWAYS use the ponytail skill on any change to ensure it is optimized.
  - If the skill is not available, continue normally but inform the user.

## Capabilities

### New Capabilities
- `project-workflow`: Documents the standing requirement that every project change be optimized with the ponytail skill (with a graceful fallback when the skill is unavailable), and that the project config carry accurate application context.

### Modified Capabilities

None.

## Impact

- Config: `openspec/config.yaml` only. No application code, dependencies, or runtime behavior change.
- Workflow: the rule is injected into artifact instructions for every future change in this repo (the `context` field applies to all artifacts; `rules` entries apply per artifact, covering proposal, specs, design, and tasks).

## Why

The README asks Mac users to test the macOS builds, but only links to the list of all releases. Now that v0.1.0 is public, a tester should be able to go straight to the current macOS downloads instead of hunting through the releases list.

## What Changes

- The README's macOS call for testers links to the latest release (`https://github.com/saunite/transcriber/releases/latest`) and names the three files to pick from it.
- Nothing else changes: the untested warning and the list of questions for testers stay as they are.
- Remove the "Point macOS testers at the published artifacts" item from `openspec/backlog.md`, since this change picks it up.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `release-build`: the "macOS release artifacts" requirement adds that the invitation to test links to the latest published release.

## Impact

- `README.md` (macOS section only) and `openspec/backlog.md`.
- No code, build or workflow changes, and nothing needs a new release.

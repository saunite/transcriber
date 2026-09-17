## Why

`tests/test_package_repos.py` takes about 192 s and needs a container runtime and the network. It checks packaging code that rarely changes, yet `run_tests.py` runs it every time, so a full run went from about 100 s to about 5 minutes. `CONTRIBUTING.md` doesn't mention the suite at all.

## What Changes

- `tests/test_package_repos.py` runs its checks only when `TRANSCRIBER_TEST_PACKAGING=1` is set. Without it, each check prints `SKIP` with how to turn it on, and the suite passes. This matches how the speech check behaves without `TRANSCRIBER_TEST_SPEECH`.
- `run_tests.py` is unchanged. It still runs every suite; this one just skips unless asked.
- `CONTRIBUTING.md`:
  - adds the suite to the table of suites;
  - explains the variable, what the suite needs (podman or docker, network) and how long it takes;
  - says when to set it: when changing `mark_package_configs.py`, `build_repo_metadata.py`, `packaging/`, the package mappings in `tauri.conf.json` or `.github/workflows/publish-repos.yml`, and before tagging a release.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `automated-tests`: adds a requirement that the container-based package repository checks are opt-in and report a skip when not requested.

## Impact

- `tests/test_package_repos.py` (a few lines in `main()`), `CONTRIBUTING.md`.
- No change to the release or publish workflows; neither runs this suite.

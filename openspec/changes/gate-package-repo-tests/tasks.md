# Tasks

## 1. Gate the suite

- [x] 1.1 In `tests/test_package_repos.py`, have `main()` print `SKIP  <check>: set TRANSCRIBER_TEST_PACKAGING=1 to run (needs podman or docker, network, ~3 min)` for each check and return 0 unless `TRANSCRIBER_TEST_PACKAGING` is `1`; update the docstring's `Run:` line to `TRANSCRIBER_TEST_PACKAGING=1 python tests/test_package_repos.py`. Verify: without the variable it prints three `SKIP` lines, exits 0 within a few seconds, and `podman ps -a` shows no new containers.
- [x] 1.2 Verify with the variable set: `TRANSCRIBER_TEST_PACKAGING=1 .venv/bin/python tests/test_package_repos.py` prints three `PASS` lines and exits 0.

  **Done 2026-09-17:** three `PASS`, exit 0, in 3:51 (the earlier measurement was 192 s), so the skip message and the docs say about 4 minutes rather than 3.

## 2. Contributor document

- [x] 2.1 In `CONTRIBUTING.md`, add a `tests/test_package_repos.py` row to the suite table, and a short paragraph after the speech-recording note: what `TRANSCRIBER_TEST_PACKAGING=1` turns on, that it needs podman or docker and the network and takes about 3 minutes, and to set it when changing `mark_package_configs.py`, `build_repo_metadata.py`, `packaging/`, the package file mappings in `src-tauri/tauri.conf.json` or `.github/workflows/publish-repos.yml`, and before tagging a release. Run the no-ai-slop skill in detect mode on the new text and fix what it flags. Verify with `grep -n TRANSCRIBER_TEST_PACKAGING CONTRIBUTING.md`.

## 3. Whole suite

- [x] 3.1 Run `.venv/bin/python run_tests.py` without the variable and verify every suite passes (or skips as documented), `tests/test_package_repos.py` reports in a few seconds, and the total is back near the pre-change ~100 s. Record the total.

  **Done 2026-09-17:** 18/18 suites passed in 96.1 s, with `tests/test_package_repos.py` reporting in 0.1 s (it had taken about 3–4 minutes of every run). A separate run of `tests/test_e2e_linux.py` had no skips, and its online update check read "You're up to date (0.1.0)".
- [x] 3.2 Run `openspec validate gate-package-repo-tests --strict` and verify it passes.

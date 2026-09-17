# Tasks

## 1. README

- [x] 1.1 In `README.md`'s macOS section, link the call for testers to `https://github.com/saunite/transcriber/releases/latest` and name the three files there (`Transcriber_<version>_aarch64.dmg`, `Transcriber_<version>_macos-arm64.zip`, `transcriber-cli_<version>_macos-arm64.tar.gz`), keeping the untested warning and the questions. Verify with `curl -sI https://github.com/saunite/transcriber/releases/latest` that the link redirects to the current tag, and that `gh release view --json assets` on that tag lists all three files.
- [x] 1.2 Run the no-ai-slop skill in detect mode on the changed lines, fix anything it flags, and verify the README still renders the section as before (`grep -n -A6 "### macOS" README.md`).

## 2. Housekeeping

- [x] 2.1 Remove "Point macOS testers at the published artifacts" (item 5 of the real-release group) from `openspec/backlog.md`, and verify with `grep -n "macOS testers" openspec/backlog.md` that it is gone.
- [x] 2.2 Run `openspec validate point-macos-testers-to-release --strict` and verify it passes.

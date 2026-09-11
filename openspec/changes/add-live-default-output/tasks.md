## 1. Default output for live capture

- [x] 1.1 In `transcriber.py`, add the `--no-output` flag, fix `--output`'s help text, and add `_live_output_path(args, now)` (design.md Decision 1). Wire it into `main()` after `parse_args()`, with a `parser.error` when both flags are given (Decision 2). Verify that `test_live_default_output.py` passes, covering four cases: explicit path kept; bare live gives the stamped name; `--no-output` gives none; not live gives none. Also verify that `transcriber.py --live --output a.txt --no-output` exits non-zero with the conflict message, and that the existing `test_*.py` files still pass.
- [x] 1.2 Update README: the live-capture examples note the default `transcript_<stamp>.txt` file and `--no-output`, and the options list documents `--no-output` and the corrected `--output` default. Verify by reading each README statement against `--help`'s output.
- [x] 1.3 On the Fedora machine, run a bare `.venv/bin/python transcriber.py --live --include-mic` for a few seconds with speech, and stop it. Verify that the first line is `Transcriber → transcript_<stamp>.txt`, and that the file exists afterwards and contains the printed lines.

  **Verified by the user 2026-09-11:** a bare live run printed `Transcriber → transcript_<stamp>.txt`, and the file was generated correctly.

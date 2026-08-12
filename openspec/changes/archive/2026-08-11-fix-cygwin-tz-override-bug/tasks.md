## 1. Fix the environment bug

- [x] 1.1 In `transcriber.py`, add `import os` and `os.environ.pop("TZ", None)` as the very first lines of the file, before any other import (including `sys`, `argparse`, `datetime`, and the local `audio_extractor`/`audio_capture`/`transcription_engine` imports).

## 2. Verify

- [x] 2.1 With `$env:TZ` unset, confirm `python transcriber.py --list-devices` (or any quick invocation) still runs correctly and, separately, confirm `datetime.now()` in a throwaway check matches the real clock.
- [x] 2.2 With `$env:TZ` set to an IANA-style value (e.g. `America/New_York`, matching what Cygwin exports), confirm timestamps produced by the fixed `transcriber.py` now match the real local clock instead of shifting to UTC.

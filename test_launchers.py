#!/usr/bin/env python3
"""The Linux and macOS launchers work from any folder and don't pick a model
size of their own (openspec/changes/01-fix-audit-edges).

Runs each script from a temporary checkout layout whose .venv python is a stub
that records its arguments, from a different current folder. No model, audio
or real engine is involved. Run: python test_launchers.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STUB = """#!/usr/bin/env bash
printf '%s\\n' "$@" > "$ARGS_FILE"
"""


def check(script):
    with tempfile.TemporaryDirectory() as tmp:
        checkout, elsewhere = Path(tmp, "checkout"), Path(tmp, "elsewhere")
        (checkout / ".venv" / "bin").mkdir(parents=True)
        elsewhere.mkdir()
        shutil.copy(ROOT / script, checkout / script)
        (checkout / "transcriber.py").write_text("")
        python = checkout / ".venv" / "bin" / "python"
        python.write_text(STUB)
        python.chmod(0o755)
        args_file = Path(tmp, "args.txt")

        result = subprocess.run(["bash", str(checkout / script), "--model-path", "/models/small"],
                                cwd=elsewhere, capture_output=True, text=True,
                                env={**os.environ, "ARGS_FILE": str(args_file)}, timeout=30)
        assert result.returncode == 0, f"{script} exited {result.returncode}: {result.stderr}"
        argv = args_file.read_text().splitlines()

    assert argv[0] == str(checkout / "transcriber.py"), f"{script} ran {argv[0]!r}, not the checkout's transcriber.py"
    assert "--model" not in argv, f"{script} passes its own --model: {argv}"
    assert argv[argv.index("--model-path") + 1] == "/models/small" and "--actual-time" in argv, argv
    output = argv[argv.index("--output") + 1]
    assert not os.path.isabs(output) and output.startswith("meeting_"), f"{script} output {output!r}"
    print(f"OK: {script} runs the checkout's transcriber.py from any folder, with no --model of its own")


def main() -> int:
    for script in ("linux-start-transcription.sh", "mac-start-transcription.sh"):
        check(script)
    print("test_launchers: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

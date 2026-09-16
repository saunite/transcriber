#!/usr/bin/env python3
"""The engine stamps in the timezone its session is configured to use, and says
which one that is (openspec/changes/fix-engine-timezone-override).

An hour's gap was once seen between the app's clock and the engine's. It never
reproduced, and both suspected causes were disproven: the engine follows `TZ`,
and neither runtime carries stale daylight-saving rules. These checks pin the
behaviour that was found to be correct, so a later change cannot quietly
introduce the defect that was suspected, and confirm the engine names the zone
it resolved -- which is what the original investigation had to work out by hand.

No model, audio or transcription is involved: the stamp comes from the same
helper every live line uses. Run: python test_engine_timezone.py
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
FAR_AWAY = "Pacific/Kiritimati"  # +14, so no offset confusion with anywhere local
PROGRAM = "import transcriber, time; print(transcriber._wall_clock_stamp()); print(time.tzname[0])"


def stamp_with(tz: str | None) -> tuple[datetime, str]:
    """(stamp the engine would print, the zone abbreviation it resolved)."""
    env = {k: v for k, v in os.environ.items() if k != "TZ"}
    if tz:
        env["TZ"] = tz
    done = subprocess.run([sys.executable, "-c", PROGRAM], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, f"the engine failed to start:\n{done.stderr[-800:]}"
    stamp, tzname = [l for l in done.stdout.splitlines() if l.strip()][-2:]
    return datetime.strptime(stamp.strip("[]"), "%Y-%m-%d %H:%M:%S"), tzname


def check_follows_tz():
    """Started with a TZ the platform can read, the engine stamps in that zone."""
    stamped, tzname = stamp_with(FAR_AWAY)
    expected = datetime.now(ZoneInfo(FAR_AWAY)).replace(tzinfo=None)
    drift = abs((stamped - expected).total_seconds())
    assert drift < 120, (
        f"with TZ={FAR_AWAY} the engine stamped {stamped} ({tzname}), "
        f"but that zone reads {expected}: {drift / 3600:.1f} hours out"
    )
    return f"TZ={FAR_AWAY} -> {stamped} ({tzname})"


def check_default_zone():
    """With no TZ set, it stamps the machine's own local time."""
    stamped, tzname = stamp_with(None)
    drift = abs((stamped - datetime.now()).total_seconds())
    assert drift < 120, f"without TZ the engine stamped {stamped} ({tzname}), {drift / 3600:.1f} hours from local time"
    return f"no TZ -> {stamped} ({tzname})"


def check_reports_its_zone():
    """The compact line a live session prints names the zone it resolved."""
    import transcriber

    line = transcriber._timezone_summary()
    stamped, tzname = stamp_with(None)
    assert tzname in line, f"the summary {line!r} does not name the zone the engine resolved ({tzname})"
    assert datetime.now().astimezone().strftime("%z")[:3] in line.replace("UTC", ""), (
        f"the summary {line!r} does not carry the offset"
    )
    return line


def main() -> int:
    if platform.system() == "Windows":
        print("SKIP  engine timezone: Windows deletes an unparseable TZ on purpose (fix-cygwin-tz-override-bug)")
        return 0
    failures = 0
    for name, check in (("engine follows TZ", check_follows_tz),
                        ("engine uses the machine's zone by default", check_default_zone),
                        ("engine reports the zone it resolved", check_reports_its_zone)):
        try:
            print(f"PASS  {name}: {check()}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL  {name}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

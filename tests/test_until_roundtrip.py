#!/usr/bin/env python3
"""Pins finding 026: iCalendar UNTIL -> JSCalendar "until" -> iCalendar UNTIL is
not the identity in the repeated local hour, and can shorten a recurrence set.

Two independent routes to the same numbers, which is the point of the test.

Route 1 derives everything from `zoneinfo` and the quoted rules, in
findings/repro/026-until-roundtrip.py.  Route 2 expands the original rule and the
round-tripped rule with python-dateutil, an actual recurrence engine that knows
nothing about JSCalendar, and counts instances.

If a future tz database changed Europe/Berlin's 2024 transition the derivation
would move, so route 1 asserts the transition itself rather than assuming it.
"""
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import env  # noqa: E402

BERLIN = ZoneInfo("Europe/Berlin")
UTC = timezone.utc

ORIGINAL_UNTIL = "20241027T013000Z"
ROUNDTRIPPED_UNTIL = "20241027T003000Z"
DTSTART_LOCAL = datetime(2024, 10, 26, 2, 45)
RULE = "FREQ=DAILY;UNTIL=%s"

failures = []


def check(label, got, want):
    if got != want:
        failures.append("%s: got %r, want %r" % (label, got, want))
    return got == want


def tzdb_precondition():
    """Local 02:30 on 2024-10-27 must be the repeated hour in Europe/Berlin."""
    first = datetime(2024, 10, 27, 2, 30, tzinfo=BERLIN, fold=0).astimezone(UTC)
    second = datetime(2024, 10, 27, 2, 30, tzinfo=BERLIN, fold=1).astimezone(UTC)
    check("tzdb: fold=0 instant", first, datetime(2024, 10, 27, 0, 30, tzinfo=UTC))
    check("tzdb: fold=1 instant", second, datetime(2024, 10, 27, 1, 30, tzinfo=UTC))


def route1_derivation():
    # The file name is not an importable identifier, so load it as a script.
    import runpy
    path = os.path.join(ROOT, "findings", "repro", "026-until-roundtrip.py")
    ns = runpy.run_path(path)
    until = datetime(2024, 10, 27, 1, 30, tzinfo=UTC)
    local = ns["ical_to_jscalendar"](until)
    check("route1: JSCalendar until", local.isoformat(), "2024-10-27T02:30:00")
    back = ns["jscalendar_to_ical"](local)
    check("route1: round-tripped UNTIL", ns["fmt_utc"](back), ROUNDTRIPPED_UNTIL)
    check("route1: round trip is not the identity", back == until, False)


def route2_dateutil():
    env.add_dateutil_to_path()
    from dateutil.rrule import rrulestr
    dtstart = DTSTART_LOCAL.replace(tzinfo=BERLIN)
    counts = {}
    for until in (ORIGINAL_UNTIL, ROUNDTRIPPED_UNTIL):
        counts[until] = len(list(rrulestr(RULE % until, dtstart=dtstart)))
    check("route2: instances before conversion", counts[ORIGINAL_UNTIL], 2)
    check("route2: instances after conversion", counts[ROUNDTRIPPED_UNTIL], 1)


def main():
    tzdb_precondition()
    route1_derivation()
    route2_dateutil()
    if failures:
        print("FAIL")
        for f in failures:
            print("  " + f)
        return 1
    print("test_until_roundtrip: ok "
          "(UNTIL %s -> \"2024-10-27T02:30:00\" -> %s; 2 instances become 1)"
          % (ORIGINAL_UNTIL, ROUNDTRIPPED_UNTIL))
    return 0


if __name__ == "__main__":
    sys.exit(main())

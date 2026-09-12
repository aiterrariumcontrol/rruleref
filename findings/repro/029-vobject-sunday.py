#!/usr/bin/env python3
"""Reproduces finding 029: sabre/vobject's two Sunday manifestations.

Needs the PHP adapter set up -- see conformance/adapters/php/README.md
(php-cli, php-xml, composer install). Run from the repository root:

    python3 findings/repro/029-vobject-sunday.py

Three checks, each independent of this repository's `expect` values:

 1. FREQ=YEARLY;BYDAY=SU;BYYEARDAY=60 does not terminate. The adapter's
    per-case alarm turns that into a reported error; without the alarm the
    process spins indefinitely.
 2. FREQ=YEARLY;BYWEEKNO=20;BYDAY=SU silently returns the Sunday of the week
    *before* the selected ISO week, from the second occurrence onward.
 3. FREQ=DAILY;BYMONTHDAY=... ignores BYMONTHDAY entirely.

1 and 2 share one cause: `RRuleIterator::$dayMap` numbers Sunday 0 (PHP's
`w`), while the BYYEARDAY and BYWEEKNO branches consume that number as
ISO-8601 (`N` / `setISODate`), where Sunday is 7.
"""
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
ADAPTER = ["php", str(ROOT / "conformance/adapters/php/vobject_adapter.php")]
DATEUTIL = [sys.executable, str(ROOT / "conformance/adapters/dateutil_adapter.py")]

CASES = [
    {"id": "hang-yearday", "rrule": "FREQ=YEARLY;BYDAY=SU;BYYEARDAY=60",
     "dtstart": "20260301T090000", "limit": 5},
    {"id": "hang-ordwk", "rrule": "FREQ=YEARLY;BYYEARDAY=100,1;BYDAY=1WE,-1MO",
     "dtstart": "20310101T090000", "limit": 5},
    {"id": "weekno-su", "rrule": "FREQ=YEARLY;BYWEEKNO=20;BYDAY=SU",
     "dtstart": "20260517T090000", "limit": 3},
    {"id": "weekno-mo", "rrule": "FREQ=YEARLY;BYWEEKNO=20;BYDAY=MO",
     "dtstart": "20260511T090000", "limit": 3},
    {"id": "daily-bymonthday", "rrule": "FREQ=DAILY;BYDAY=FR;BYMONTHDAY=15",
     "dtstart": "20270115T090000", "limit": 4},
]


def run(cmd, env=None):
    payload = "".join(json.dumps(c) + "\n" for c in CASES)
    out = subprocess.run(cmd, input=payload, capture_output=True, text=True,
                         timeout=300, env=env).stdout
    return {json.loads(l)["id"]: json.loads(l) for l in out.splitlines() if l.strip()}


env = dict(os.environ, TZ="UTC", RRULE_CASE_TIMEOUT="5")
php = run(ADAPTER, env)
du = run(DATEUTIL, env)

for case in CASES:
    i = case["id"]
    print(f"{i}\n  {case['rrule']}  DTSTART:{case['dtstart']}")
    for name, got in (("sabre/vobject", php[i]), ("python-dateutil", du[i])):
        if "error" in got:
            print(f"    {name:16} error: {got['error']}")
        else:
            print(f"    {name:16} {got['occurrences']}")
    print()

print("ISO week 20 of 2027 is Mon 2027-05-17 .. Sun 2027-05-23:")
import datetime
for d in (datetime.date(2027, 5, 16), datetime.date(2027, 5, 23)):
    print(f"  {d}  isocalendar={d.isocalendar()}")

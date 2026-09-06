#!/usr/bin/env python3
"""Finding 008: week numbering at the year boundary.

Pins three things:
  1. the RFC 5545 3.3.10 definition, checked against date.isocalendar();
  2. this project's expander agreeing with that definition on the five
     previously unadjudicated disputes;
  3. the *current* dateutil behaviour, so that installing a version carrying
     dateutil/dateutil#1537 makes this test fail loudly rather than silently
     changing what the corpus disagrees with.
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

from byweekno_check import self_check, sweep, week_number, weeks_in_year  # noqa: E402
from naive import expand  # noqa: E402

fails = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name)
    if not ok:
        print("    want", want)
        print("    got ", got)
        fails.append(name)


print("RFC 3.3.10 week numbering vs date.isocalendar()")
check("109938 days 1900-2200, WKST=MO", self_check(), 109938)

print("the RFC's own note: week 53 needs Thu Jan 1, or Wed Jan 1 in a leap year")
check("2038 has 52 weeks (Jan 1 is a Friday)", weeks_in_year(2038, "MO"), 52)
check("2026 has 53 weeks (Jan 1 is a Thursday)", weeks_in_year(2026, "MO"), 53)
check("2039-01-01 is week 52 of 2038", week_number(datetime(2039, 1, 1).date(), "MO"), (2038, 52))

print("naive agrees with the adjudicated expectations (corpus/adjudications.json)")
adj = json.load(open(os.path.join(ROOT, "corpus", "adjudications.json")))["cases"]
check("five adjudicated BYWEEKNO cases", len(adj), 5)
for key, a in sorted(adj.items()):
    rule, ds = key.split("|")
    dtstart = datetime.strptime(ds, "%Y%m%dT%H%M%S")
    got = [d.strftime("%Y%m%dT%H%M%S") for d in expand(rule, dtstart)][:len(a["expected"])]
    check(rule, got, a["expected"])

print("installed dateutil, against the same definition")
try:
    from dateutil.rrule import rrulestr
    import dateutil
    bad = {r["rule"]: (len(r["spurious"]), len(r["missing"]))
           for r in sweep(rrulestr) if r["spurious"] or r["missing"]}
    check("dateutil version", dateutil.__version__, "2.9.0.post0")
    check("mismatching sweeps (defects A and B)", sorted(bad), [
        "FREQ=YEARLY;BYWEEKNO=-53;WKST=MO", "FREQ=YEARLY;BYWEEKNO=-53;WKST=SU",
        "FREQ=YEARLY;BYWEEKNO=-53;WKST=WE",
        "FREQ=YEARLY;BYWEEKNO=52;WKST=MO", "FREQ=YEARLY;BYWEEKNO=52;WKST=SU",
        "FREQ=YEARLY;BYWEEKNO=52;WKST=WE",
        "FREQ=YEARLY;BYWEEKNO=53;WKST=MO", "FREQ=YEARLY;BYWEEKNO=53;WKST=SU",
        "FREQ=YEARLY;BYWEEKNO=53;WKST=WE"])
    check("week 53 spurious / week 52 missing are the same 18 days (WKST=MO)",
          (bad["FREQ=YEARLY;BYWEEKNO=53;WKST=MO"][0],
           bad["FREQ=YEARLY;BYWEEKNO=52;WKST=MO"][1]), (18, 18))
except ImportError:
    print("  skip  dateutil not importable")

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)

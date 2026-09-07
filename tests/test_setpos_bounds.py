"""Regression: a bound must not truncate the period BYSETPOS selects from.

RFC 5545 3.3.10 orders the evaluation outright -- "... BYSECOND and BYSETPOS;
then COUNT and UNTIL are evaluated" -- so UNTIL cannot be allowed to shrink
the candidate set BYSETPOS chooses within. `naive.expand` folded UNTIL, and
separately the caller's horizon, into the candidate stream and did exactly
that. Found by property P3 on 2026-09-07; see findings/014.

Expected values here are derived by hand from the rule, not taken from either
expander, and both expanders are held to them.
"""
import os
import sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
from expanders import EXPANDERS  # noqa: E402

FMT = "%Y%m%dT%H%M%S"
fails = []

# rule, dtstart, horizon_days, expected -- reasoned, not generated:
#
# 1. Each day offers 08:00 and 09:00; BYSETPOS=-1 takes 09:00. UNTIL falls one
#    second before 5 March 09:00, so 5 March contributes nothing at all. The
#    wrong answer is 20260305T080000: that is the period truncated first.
# 2. Same rule, UNTIL exactly on an occurrence: inclusive, so it is kept.
# 3. September only, 15th and last day; BYSETPOS=-1 takes the last day. The
#    horizon stops one day before 30 September 2030, so 2030 contributes
#    nothing. The wrong answer is 20300915T090000.
CASES = [
    ("FREQ=DAILY;BYHOUR=9,8;BYSETPOS=-1;UNTIL=20260305T085959",
     "20260302T090000", 3650,
     ["20260302T090000", "20260303T090000", "20260304T090000"]),
    ("FREQ=DAILY;BYHOUR=9,8;BYSETPOS=-1;UNTIL=20260305T090000",
     "20260302T090000", 3650,
     ["20260302T090000", "20260303T090000", "20260304T090000",
      "20260305T090000"]),
    ("FREQ=MONTHLY;BYMONTH=9;BYMONTHDAY=15,-1;BYSETPOS=-1",
     "20270930T090000", 365 * 3,
     ["20270930T090000", "20280930T090000", "20290930T090000"]),
]


def test_bounds_are_applied_after_bysetpos():
    for rule, ds, days, want in CASES:
        d0 = datetime.strptime(ds, FMT)
        for name, exp in sorted(EXPANDERS.items()):
            got = [t.strftime(FMT)
                   for t in exp(rule, d0, d0 + timedelta(days=days), 100)]
            if got != want:
                fails.append("%s: %s\n    got  %s\n    want %s"
                             % (name, rule, got, want))


if __name__ == "__main__":
    test_bounds_are_applied_after_bysetpos()
    print("%d checks failed" % len(fails))
    for f in fails:
        print("  " + f)
    sys.exit(1 if fails else 0)

#!/usr/bin/env python3
"""Finding 117. Duplicate-value coverage in the corpus, and property P8.

    python3 findings/repro/117-duplicate-byvalue.py          # ~2s

Prints, in order: how much of the corpus repeats a value inside one BY-list
and how much of that also carries an explicit COUNT; the expansion that
property P8 was written for, before and after the fix to `naive.parse`; and
P8's verdict on every in-process expander.

The "before" line is produced by re-running the parse with deduplication
disabled, so it is a live demonstration of the defect rather than a quotation
of one.
"""
import json
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))
import naive              # noqa: E402
import properties as P    # noqa: E402
from expanders import EXPANDERS  # noqa: E402

FMT = "%Y%m%dT%H%M%S"


def repeats_a_value(rule):
    for part in rule.split(";"):
        if "=" not in part:
            continue
        _, v = part.split("=", 1)
        if "," in v and len(v.split(",")) != len(set(v.split(","))):
            return True
    return False


def main():
    path = os.path.join(ROOT, "corpus", "corroborated.json")
    doc = json.load(open(path))
    cases = doc if isinstance(doc, list) else doc.get("cases", doc)
    dups = [c for c in cases if repeats_a_value(c["rrule"])]
    bounded = [c for c in dups if "COUNT=" in c["rrule"]]

    print("corpus/corroborated.json")
    print("  cases                                      (%d of %d)" % (len(cases), len(cases)))
    print("  repeat a value inside one BY-list          (%d of %d)" % (len(dups), len(cases)))
    print("  ... and also carry an explicit COUNT       (%d of %d)" % (len(bounded), len(dups)))
    for c in dups:
        print("      %s" % c["rrule"])

    print()
    print("the shape P8 was written for, FREQ=MINUTELY;COUNT=12;BYSECOND=...")
    dtstart = datetime(2008, 1, 1, 9, 0, 0)
    real = naive._dedupe
    for label, dedupe in (("naive, before the fix", lambda xs: xs),
                          ("naive, after the fix ", real)):
        naive._dedupe = dedupe
        try:
            for seconds in ("0,30", "0,30,0"):
                rule = "FREQ=MINUTELY;COUNT=12;BYSECOND=" + seconds
                got = naive.expand(rule, dtstart)
                print("  %s  BYSECOND=%-7s %2d emitted, %2d distinct  last %s"
                      % (label, seconds, len(got), len(set(got)),
                         got[-1].strftime("%H:%M:%S") if got else "-"))
        finally:
            naive._dedupe = real

    print()
    print("P8 over every in-process expander, on that rule")
    for name, exp in EXPANDERS.items():
        r = P.p8_duplicate_value_inert(exp, "FREQ=MINUTELY;COUNT=12;BYSECOND=0,30", dtstart)
        print("  %-10s %s" % (name, r["status"]))


if __name__ == "__main__":
    main()

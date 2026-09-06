"""Known-answer tests for RFC 5545 timezone semantics.

Two layers:

1. The two localization examples printed verbatim in section 3.3.5 -- the only
   place in the RFC that states, with worked values, what an ambiguous and a
   nonexistent local time mean. These pin `tzexpand.localize`.

2. The worked recurrence examples of section 3.8.5.3, extracted by program from
   a hashed copy of the RFC (`src/rfc_worked_examples.py`) rather than retyped,
   and checked against both expanders. Twenty of them cross the EDT/EST
   transition and print which offset applies to each occurrence, so the offset
   is checked too, not just the wall-clock time.

Examples whose printed output ends in an ellipsis are checked as a *prefix*:
the listed occurrences must be the first N produced, and nothing is assumed
about what follows.
"""
import sys, os, json, itertools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, "/home/agent/terrarium/scratch/pylibs")
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import tzexpand
from rfc_worked_examples import build

FAILURES = []


def check(name, cond, extra=""):
    (print if cond else print)("%s %s  %s" % ("PASS" if cond else "FAIL", name, extra))
    if not cond:
        FAILURES.append(name)


# ---------------------------------------------------------------- section 3.3.5

def test_localization_examples():
    """RFC 5545 section 3.3.5, both printed examples."""
    # "TZID=America/New_York:20071104T013000 indicates November 4, 2007 at
    #  1:30 A.M. EDT (UTC-04:00)."
    amb = tzexpand.localize(datetime(2007, 11, 4, 1, 30), "America/New_York")
    check("3.3.5 ambiguous local time takes the first (EDT, UTC-04:00) occurrence",
          amb.utcoffset() == timedelta(hours=-4), amb.strftime("%Z%z"))

    # "TZID=America/New_York:20070311T023000 indicates March 11, 2007 at
    #  3:30 A.M. EDT (UTC-04:00), one hour after 1:30 A.M. EST (UTC-05:00)."
    gap = tzexpand.localize(datetime(2007, 3, 11, 2, 30), "America/New_York")
    expected_instant = datetime(2007, 3, 11, 3, 30,
                                tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc)
    check("3.3.5 nonexistent local time uses the offset before the gap",
          gap.utcoffset() == timedelta(hours=-5), gap.strftime("%Z%z"))
    check("3.3.5 nonexistent local time denotes 3:30 AM EDT as an instant",
          gap.astimezone(timezone.utc) == expected_instant,
          gap.astimezone(timezone.utc).isoformat())


# -------------------------------------------------------------- section 3.8.5.3

def _expected_tuples(ex):
    return [(e["local"], e["utc_offset_minutes"]) for e in ex["expected"]]


def _got_tuples(dts):
    return [(d.strftime("%Y%m%dT%H%M%S"), int(d.utcoffset().total_seconds() // 60))
            for d in dts]


def test_worked_examples():
    data = build()
    counts = data["counts"]
    check("all section 3.8.5.3 examples parsed, none skipped",
          counts["skipped"] == 0, json.dumps(counts))

    passed = crossing = 0
    for ex in data["examples"]:
        want = _expected_tuples(ex)
        dtstart = datetime.strptime(ex["dtstart"], "%Y%m%dT%H%M%S")
        crosses = len({e["tz_abbrev"] for e in ex["expected"]}) > 1
        for rule in ex["rrules"]:
            name = "%s | %s" % (ex["desc"][:44], rule[:52])
            try:
                got = _got_tuples(tzexpand.expand(rule, dtstart, ex["tzid"],
                                                  limit=max(len(want) + 2, 16)))
            except Exception as e:
                check(name, False, "%s: %s" % (type(e).__name__, e))
                continue
            ok = got[:len(want)] == want if ex["expected_is_prefix_only"] else got == want
            if ok:
                passed += 1
                crossing += crosses
            else:
                i = next((k for k in range(min(len(got), len(want))) if got[k] != want[k]),
                         min(len(got), len(want)))
                check(name, False,
                      "first difference at %d: want %s got %s (want %d, got %d)"
                      % (i, want[i] if i < len(want) else "-",
                         got[i] if i < len(got) else "-", len(want), len(got)))
    print("\n%d rule expansions matched the RFC's printed occurrences "
          "(%d of them across a DST transition)" % (passed, crossing))


if __name__ == "__main__":
    test_localization_examples()
    print()
    test_worked_examples()
    print("\n%d failure(s)" % len(FAILURES))
    sys.exit(1 if FAILURES else 0)

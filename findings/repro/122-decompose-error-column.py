#!/usr/bin/env python3
"""122: split `DateTime::Event::ICal`'s error column into the clock and the
library, using a deadline the clock part cannot survive.

  # ~24 minutes; score.py's default --timeout 900 is a WHOLE-RUN budget and
  # is not enough (finding 116).
  RRULE_CASE_TIMEOUT=10 python3 conformance/score.py --timeout 7200 \
      --json /tmp/d10.json -- perl conformance/adapters/perl/dtical_adapter.pl
  python3 findings/repro/122-decompose-error-column.py /tmp/d10.json

WHY A SCORE RUN IS NEEDED AT ALL when finding 122's timing pass already knows
which cases are slow.  Because the two halves of that column are told apart by
the adapter's error MESSAGE, and `score.py --json` is the only thing that keeps
messages.  Finding 116's stored rescore keeps case ids without them, which is
why finding 073 -- whose whole subject is splitting error columns this way --
has a split for `sabre` and `ical.js` and never had one for this adapter.

WHY DEADLINE 10 AND NOT 20.  Either would separate the two halves, but 10 is
the value finding 114 found two documents claiming, so one run answers both
questions: what the wrong deadline would have published, and how much of the
right deadline's error column is the library rather than the load.

A REFUSAL IS DEADLINE-INDEPENDENT and that is checked, not assumed: every
refusal found here must also be in finding 116's error bucket, which was scored
at the real deadline of 20. If a case could refuse at one deadline and not at
another, nothing below would mean anything.
"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
TIMES = os.path.join(REPO, "findings", "data", "122-dtical-case-times.json")
R116 = os.path.join(REPO, "findings", "data",
                    "116-dtical-quiet-machine-rescore.json")
OUT = os.path.join(REPO, "findings", "data",
                   "122-error-column-decomposition.json")
# The exact string dtical_adapter.pl emits when its alarm fires. Anchored, so a
# library message that merely mentions time cannot be miscounted as the clock.
ALARM = re.compile(r"^no answer within \d+s$")


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    sc = json.load(open(argv[0]))
    deadline = int(os.environ.get("RRULE_CASE_TIMEOUT", 10))
    rows = [(f["case"]["id"], str((f.get("reply") or {}).get("error", "")))
            for f in sc["failures"] if f["bucket"] == "error"]
    alarm = sorted(i for i, m in rows if ALARM.match(m))
    refuse = sorted((i, m) for i, m in rows if not ALARM.match(m))

    err116 = set(json.load(open(R116))["buckets"]["error"])
    stray = [i for i, _ in refuse if i not in err116]
    times = {d["id"]: d["ms"]
             for d in json.load(open(TIMES))["slow"]}

    # The library's refusals, grouped by shape rather than listed: the file
    # paths and the specific integers in "byminute=0,30" are incidental.
    shapes = collections.Counter(
        re.sub(r"=[-\d,]+", "=...", m.split(" at /")[0]) for _, m in refuse)

    res = {
        "finding": 122,
        "scored_at_deadline_seconds": deadline,
        "counts_at_this_deadline": sc["counts"],
        "error_split": {"clock": len(alarm), "library": len(refuse)},
        "library_refusal_shapes": dict(shapes),
        "library_refusal_ids": [i for i, _ in refuse],
        "every_refusal_is_also_error_at_deadline_20": not stray,
        "clock_ids": alarm,
        "published_row_decomposition": {
            "note": "finding 116 scored 124 errors at the real deadline of 20. "
                    "A refusal does not depend on the deadline, so that column "
                    "is this run's library count plus whatever the clock took "
                    "in THAT run -- which is not the same set the clock took in "
                    "finding 122's timing pass.",
            "error_column": len(err116),
            "library": len(set(i for i, _ in refuse) & err116),
            "clock_in_116s_run": len(err116 - set(i for i, _ in refuse)),
        },
        # The timing artifact stores nothing below its floor, so a missing id
        # means "faster than the floor" and must not be read as 0ms.
        "clock_cases_timed_under_this_deadline": sorted(
            ({"id": i, "ms": times[i]} for i in alarm
             if i in times and times[i] < deadline * 1000),
            key=lambda d: d["ms"]),
        "clock_cases_below_the_timing_floor": sorted(
            i for i in alarm if i not in times),
    }
    json.dump(res, open(OUT, "w"), indent=1, sort_keys=True)
    open(OUT, "a").write("\n")

    print("scored at deadline %ds: %s" % (deadline, sc["counts"]))
    print("error column %d = %d clock + %d library"
          % (len(rows), len(alarm), len(refuse)))
    print("every refusal is also an error at deadline 20: %s"
          % ("yes" if not stray else "NO -- %d strays" % len(stray)))
    print("\nthe library half, by shape:")
    for shape, n in shapes.most_common():
        print("  %4d  %s" % (n, shape))
    pd = res["published_row_decomposition"]
    print("\nthe published row's %d-case error column: %d library + %d clock"
          % (pd["error_column"], pd["library"], pd["clock_in_116s_run"]))
    under = res["clock_cases_timed_under_this_deadline"]
    print("\ncases the alarm took here that the timing pass measured UNDER %ds "
          "(%d):" % (deadline, len(under)))
    for d in under:
        print("  %6dms  %s" % (d["ms"], d["id"]))
    print("\nwrote %s" % os.path.relpath(OUT, REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

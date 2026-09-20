#!/usr/bin/env python3
"""Decide, soundly and in finite time, whether a recurrence rule is empty.

The corpus records `expect: []` for cases where the naive expander found
nothing inside `naive.HORIZON_DAYS`. That is an *observation*, not a proof: it
says only that no occurrence was seen inside the window. This module supplies
the proof.

THE ARGUMENT
------------
The proleptic Gregorian calendar is exactly periodic with period

    C = 146097 days = 400 years = 4800 months = 20871 weeks

and 146097 is divisible by 7, so weekday and ISO-week structure repeat with it
too. Every RFC 5545 `BY*` part is a predicate on a date's position within that
structure -- month, month-day, year-day, weekday, ISO week number -- and none
of them consults the absolute year. `BYSETPOS` and `WKST` operate on the set a
period yields, so they inherit the same periodicity.

What does *not* automatically repeat is the sequence of interval periods: with
`INTERVAL=k` the rule only examines every k-th period counted from `DTSTART`.
That sequence realigns after `lcm(cycle_length_in_periods, k)` periods. So for
a rule with neither `UNTIL` nor `COUNT`, the whole recurrence set is periodic
with period

    FREQ=YEARLY   lcm(400, k)   years
    FREQ=MONTHLY  lcm(4800, k)  months
    FREQ=WEEKLY   lcm(20871, k) weeks
    FREQ=DAILY    lcm(146097, k) days

Therefore: **if no occurrence falls in [DTSTART, DTSTART + P), none ever will.**
Searching one full period is a complete decision procedure for emptiness, and
`period_days()` below returns P.

Sub-daily frequencies are excluded. `BYHOUR`/`BYMINUTE`/`BYSECOND` expansion
within a day is trivially periodic, but a sub-daily `FREQ` makes the period a
count of hours or seconds rather than days and the argument, while still true,
is not what this module computes; see `period_days` returning None.

A cheap structural fast path is also provided. It is not needed for
correctness -- the period search decides every case -- but it discharges the
`BYSETPOS`-shaped cases without any search at all, and it states the reason in
words, which the search cannot.

Finding 067.
"""
import sys, os, json, argparse
from math import lcm
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import naive  # noqa: E402

GREGORIAN_CYCLE_DAYS = 146097
CYCLE = {"YEARLY": 400, "MONTHLY": 4800, "WEEKLY": 20871, "DAILY": GREGORIAN_CYCLE_DAYS}


def parts(rrule):
    return dict(p.split("=", 1) for p in rrule.split(";") if "=" in p)


def period_days(rrule):
    """Days in one full period of `rrule`, or None if the argument does not apply."""
    p = parts(rrule)
    freq = p.get("FREQ")
    if freq not in CYCLE:
        return None                      # sub-daily: see module docstring
    if "UNTIL" in p or "COUNT" in p:
        return None                      # finite by construction; no proof needed
    k = int(p.get("INTERVAL", "1"))
    periods = lcm(CYCLE[freq], k)
    if freq == "DAILY":
        return periods
    if freq == "WEEKLY":
        return periods * 7
    return periods // CYCLE[freq] * GREGORIAN_CYCLE_DAYS


def structural_reason(rrule):
    """A one-line proof of emptiness that needs no search, or None."""
    p = parts(rrule)
    if "BYSETPOS" not in p or any(k in p for k in ("BYHOUR", "BYMINUTE", "BYSECOND")):
        return None
    pos = [int(x) for x in p["BYSETPOS"].split(",")]
    freq = p.get("FREQ")
    if freq == "DAILY":
        # A DAILY period is one day, so the set BYSETPOS selects from holds at
        # most one element, whatever the other BY parts do to it.
        if all(abs(x) >= 2 for x in pos):
            return ("a DAILY period yields at most one candidate, "
                    "so no BYSETPOS position of magnitude 2 or more can select anything")
    if freq == "WEEKLY":
        n = len(p["BYDAY"].split(",")) if "BYDAY" in p else 1
        if all(abs(x) > n for x in pos):
            return ("a WEEKLY period yields at most %d candidate%s, "
                    "so no BYSETPOS position of magnitude above %d can select anything"
                    % (n, "" if n == 1 else "s", n))
    return None


def prove(rrule, dtstart):
    """-> dict with 'empty' (bool or None = undecidable here) and 'why'."""
    reason = structural_reason(rrule)
    if reason:
        return {"empty": True, "method": "structural", "why": reason, "period_days": None}
    P = period_days(rrule)
    if P is None:
        return {"empty": None, "method": None,
                "why": "not covered: sub-daily FREQ, or UNTIL/COUNT present", "period_days": None}
    occ = naive.expand(rrule, dtstart, horizon=dtstart + timedelta(days=P), limit=1)
    if occ:
        return {"empty": False, "method": "period-search", "period_days": P,
                "why": "witness at %s" % occ[0].strftime("%Y%m%dT%H%M%S"),
                "witness": occ[0].strftime("%Y%m%dT%H%M%S")}
    return {"empty": True, "method": "period-search", "period_days": P,
            "why": "no occurrence in one full period of %d days (%.0f years)"
                   % (P, P / 365.2425)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--corpus", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "corpus", "corroborated.json"),
        help="scan every empty-expect case in this corpus file")
    ap.add_argument("--rrule", help="prove a single rule instead")
    ap.add_argument("--dtstart", default="20260101T090000")
    ap.add_argument("--json", help="write per-case results here")
    a = ap.parse_args()

    if a.rrule:
        r = prove(a.rrule, datetime.strptime(a.dtstart, "%Y%m%dT%H%M%S"))
        print(json.dumps(r, indent=1))
        return 0

    cases = json.load(open(a.corpus))["cases"]
    empty = [c for c in cases if not c["expect"] and c.get("expect_bound") == "horizon"]
    out, proven, disproved, undecided = [], 0, 0, 0
    for c in empty:
        r = prove(c["rrule"], datetime.strptime(c["dtstart"], "%Y%m%dT%H%M%S"))
        r.update(rrule=c["rrule"], dtstart=c["dtstart"])
        out.append(r)
        proven += r["empty"] is True
        disproved += r["empty"] is False
        undecided += r["empty"] is None
    print("horizon-bounded empty cases: %d" % len(empty))
    print("  proven empty:      %d  (%d structural, %d by period search)"
          % (proven,
             sum(1 for r in out if r["method"] == "structural"),
             sum(1 for r in out if r["method"] == "period-search" and r["empty"])))
    print("  DISPROVED:         %d" % disproved)
    print("  undecided here:    %d" % undecided)
    for r in out:
        if r["empty"] is False:
            print("  !! %s %s -> %s" % (r["dtstart"], r["rrule"], r["witness"]))
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)
    return 1 if disproved else 0


if __name__ == "__main__":
    sys.exit(main())

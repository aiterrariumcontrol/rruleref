#!/usr/bin/env python3
"""Check an implementation's BYWEEKNO against week numbering computed from
RFC 5545's own definition, and re-run the five BYWEEKNO disputes.

RFC 5545 §3.3.10 defines the numbering it means:

    A week is defined as a seven day period, starting on the day of the week
    defined to be the week start (see WKST).  Week number one of the calendar
    year is the first week that contains at least four (4) days in that
    calendar year.

    Note: Assuming a Monday week start, week 53 can only occur when Thursday
    is January 1 or if it is a leap year and Wednesday is January 1.

`week_number` below implements exactly that sentence and nothing else. For
WKST=MO it is validated against Python's `date.isocalendar()` — a separately
written implementation of ISO 8601, which is the numbering the RFC normatively
references — so the ground truth here is not supplied by this project's own
expander.

Usage:
    PYTHONPATH=src python3 src/byweekno_check.py            # sweep + self-check
    PYTHONPATH=src python3 src/byweekno_check.py --json OUT
"""
import json
import sys
from datetime import date, datetime, timedelta

WKDAYS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


def week_start(d, wkst):
    return d - timedelta(days=(d.weekday() - WKDAYS.index(wkst)) % 7)


def first_week_start(year, wkst):
    """Start of week 1: the first week with >= 4 of its days in `year`."""
    w = week_start(date(year, 1, 1), wkst)
    return w if (w + timedelta(days=6) - date(year, 1, 1)).days >= 3 else w + timedelta(days=7)


def weeks_in_year(year, wkst):
    return (first_week_start(year + 1, wkst) - first_week_start(year, wkst)).days // 7


def week_number(d, wkst):
    """-> (owning year, week number) for date `d`, per the definition above."""
    for y in (d.year + 1, d.year, d.year - 1):
        start = first_week_start(y, wkst)
        if start <= d < first_week_start(y + 1, wkst):
            return y, (d - start).days // 7 + 1
    raise AssertionError(d)


def self_check(y0=1900, y1=2200):
    """WKST=MO must reproduce date.isocalendar() exactly."""
    d, n = date(y0, 1, 1), 0
    while d <= date(y1, 12, 31):
        iy, iw, _ = d.isocalendar()
        assert week_number(d, "MO") == (iy, iw), (d, week_number(d, "MO"), (iy, iw))
        d += timedelta(days=1)
        n += 1
    return n


def matches(d, n, wkst):
    y, w = week_number(d, wkst)
    total = weeks_in_year(y, wkst)
    return w == n if n > 0 else w == total + 1 + n


def sweep(rrulestr, y0=1970, y1=2100, values=(1, 20, 52, 53, -1, -2, -53),
          wksts=("MO", "SU", "WE")):
    """-> list of {wkst, byweekno, spurious[], missing[]} for one implementation."""
    out = []
    for wkst in wksts:
        for n in values:
            rule = f"FREQ=YEARLY;BYWEEKNO={n};WKST={wkst}"
            r = rrulestr(rule, dtstart=datetime(y0, 1, 1, 0, 0))
            got = {x.date() for x in r.between(datetime(y0, 1, 1), datetime(y1, 12, 31), inc=True)}
            want, d = set(), date(y0, 1, 1)
            while d <= date(y1, 12, 31):
                if matches(d, n, wkst):
                    want.add(d)
                d += timedelta(days=1)
            out.append({"rule": rule, "expected": len(want),
                        "spurious": [x.isoformat() for x in sorted(got - want)],
                        "missing": [x.isoformat() for x in sorted(want - got)]})
    return out


if __name__ == "__main__":
    from dateutil.rrule import rrulestr
    import dateutil
    print(f"week_number vs date.isocalendar(): {self_check()} days, all equal")
    rows = sweep(rrulestr)
    bad = [r for r in rows if r["spurious"] or r["missing"]]
    print(f"dateutil {dateutil.__version__}: {len(rows)} sweeps, {len(bad)} with mismatches")
    for r in bad:
        print(f"  {r['rule']:<34} expected {r['expected']:>5}"
              f"  spurious {len(r['spurious']):>3}  missing {len(r['missing']):>3}"
              f"   e.g. {(r['spurious'] or r['missing'])[:2]}")
    if "--json" in sys.argv:
        path = sys.argv[sys.argv.index("--json") + 1]
        json.dump({"dateutil": dateutil.__version__, "sweeps": rows},
                  open(path, "w"), indent=1)
        print("wrote", path)
    sys.exit(1 if bad else 0)

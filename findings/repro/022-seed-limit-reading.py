"""022 — the two readings of RFC 5545 3.3.10 for FREQ=WEEKLY with BYMONTH.

No dependencies; python3 022-seed-limit-reading.py

3.3.10 says the BYxxx parts are applied "to the current set of evaluated
occurrences" in the order BYMONTH ... BYDAY ... BYSETPOS.  For FREQ=WEEKLY,
BYMONTH is a LIMIT and BYDAY is an EXPAND.  What is "the current set" when
BYMONTH runs, before BYDAY has expanded anything?

  filter-instances : BYMONTH restricts the instants the week finally yields.
                     Every implementation measured in this project does this.
  seed-limit       : the set entering the week is the single DTSTART-derived
                     seed for that week; BYMONTH is applied to it; if the seed
                     is dropped the week yields nothing, and if it is kept
                     BYDAY expands the whole week -- including into months
                     BYMONTH does not select.

Only what these probes need is implemented: FREQ=WEEKLY, WKST=MO, BYMONTH,
BYDAY (unsigned), BYSETPOS, INTERVAL.
"""
from datetime import datetime, timedelta

DAYS = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")


def _parse(rrule):
    p = dict(kv.split("=", 1) for kv in rrule.split(";"))
    assert p["FREQ"] == "WEEKLY", "this reproducer only covers FREQ=WEEKLY"
    assert "WKST" not in p or p["WKST"] == "MO"
    return p


def expand(rrule, dtstart, limit, reading, weeks=400):
    """reading is 'filter-instances' or 'seed-limit'."""
    p = _parse(rrule)
    interval = int(p.get("INTERVAL", 1))
    bymonth = [int(x) for x in p["BYMONTH"].split(",")] if "BYMONTH" in p else None
    byday = p["BYDAY"].split(",") if "BYDAY" in p else None
    bysetpos = [int(x) for x in p["BYSETPOS"].split(",")] if "BYSETPOS" in p else None
    out = []
    for n in range(weeks):
        seed = dtstart + timedelta(weeks=n * interval)
        cur = [seed]
        if bymonth is not None and reading == "seed-limit":
            cur = [d for d in cur if d.month in bymonth]
        if byday is not None:
            new = []
            for d in cur:
                start = d - timedelta(days=d.weekday())      # WKST=MO
                new += [start + timedelta(days=k) for k in range(7)
                        if DAYS[(start + timedelta(days=k)).weekday()] in byday]
            cur = sorted(set(new))
        if bymonth is not None and reading == "filter-instances":
            cur = [d for d in cur if d.month in bymonth]
        if bysetpos is not None:
            cur = sorted({cur[i - 1 if i > 0 else len(cur) + i] for i in bysetpos
                          if 1 <= abs(i) <= len(cur)})
        out = sorted(set(out) | {d for d in cur if d >= dtstart})
        if len(out) >= limit:
            break
    return [d.strftime("%Y%m%d") for d in out][:limit]


CASES = [
    ("P1", "FREQ=WEEKLY;BYDAY=MO,SU,TU;BYMONTH=7", "20260705T090000", 15),
    ("P3", "FREQ=WEEKLY;BYDAY=MO,SU,TU;BYMONTH=7;BYSETPOS=1", "20260705T090000", 8),
    ("Q1", "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYMONTH=7;BYSETPOS=1", "20260701T090000", 6),
    ("Q4", "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYMONTH=9,10,11,12;BYSETPOS=1",
     "20260901T090000", 10),
]

if __name__ == "__main__":
    for name, rrule, ds, limit in CASES:
        dt = datetime.strptime(ds, "%Y%m%dT%H%M%S")
        print("== %s  DTSTART:%s  RRULE:%s" % (name, ds, rrule))
        for reading in ("filter-instances", "seed-limit"):
            print("   %-16s %s" % (reading, " ".join(expand(rrule, dt, limit, reading))))
        print()

"""Differential harness: naive spec-derived expander vs python-dateutil."""
import sys, random, itertools
sys.path.insert(0, "/home/agent/terrarium/scratch/pylibs")
sys.path.insert(0, "src")
from datetime import datetime, timedelta
import dateutil.rrule as du
from naive import expand
import validity

DTSTARTS = [datetime(2026, 1, 1, 9, 0, 0), datetime(2026, 3, 31, 9, 0, 0),
            datetime(2024, 2, 29, 9, 0, 0), datetime(2026, 12, 31, 9, 0, 0),
            datetime(2026, 5, 17, 9, 0, 0)]

def du_expand(rule, dtstart, n):
    try:
        it = du.rrulestr("RRULE:" + rule, dtstart=dtstart)
        return list(itertools.islice(iter(it), n))
    except Exception as e:
        return "ERROR:" + type(e).__name__

HORIZON_DAYS = 365 * 30 + 8

def compare(rule, dtstart, n=8):
    horizon = dtstart + timedelta(days=HORIZON_DAYS)
    try:
        mine = expand(rule, dtstart, limit=n)[:n]
    except Exception as e:
        return ("ERROR:" + type(e).__name__, du_expand(rule, dtstart, n))
    theirs = du_expand(rule, dtstart, n)
    if isinstance(theirs, str):
        return (mine, theirs)
    # Compare inside one independently defined bound -- the horizon -- and
    # never shorten one side to match the other. Truncating `theirs` to
    # len(mine) let an expander omit valid occurrences and still be scored as
    # agreeing: an empty output compared equal to eight occurrences. See
    # tests/test_differ.py.
    mine = [x for x in mine if x <= horizon][:n]
    theirs = [x for x in theirs if x <= horizon][:n]
    return (mine, theirs) if mine != theirs else None

def gen(rng, _depth=0):
    """Generate a random rule that is *valid* under RFC 5545 3.3.10.

    Generating rules the spec prohibits (e.g. numeric BYDAY with FREQ=YEARLY
    and BYWEEKNO) put 13 invalid cases in the corroborated corpus, where
    implementation agreement looked like conformance evidence. Rejected here
    at the source; src/validity.py is the check.
    """
    r = _gen_raw(rng)
    if validity.is_valid(r) or _depth > 20:
        return r
    return gen(rng, _depth + 1)


def _gen_raw(rng):
    freq = rng.choice(["YEARLY", "MONTHLY", "WEEKLY", "DAILY"])
    parts = ["FREQ=" + freq]
    if rng.random() < 0.3:
        parts.append("INTERVAL=%d" % rng.randint(2, 4))
    pool = []
    if freq == "YEARLY":
        pool = ["BYMONTH", "BYWEEKNO", "BYYEARDAY", "BYMONTHDAY", "BYDAY"]
    elif freq == "MONTHLY":
        pool = ["BYMONTH", "BYMONTHDAY", "BYDAY"]
    elif freq == "WEEKLY":
        pool = ["BYMONTH", "BYDAY"]
    else:
        pool = ["BYMONTH", "BYMONTHDAY", "BYDAY"]
    for name in rng.sample(pool, rng.randint(1, min(2, len(pool)))):
        parts.append(name + "=" + val(name, freq, rng))
    if rng.random() < 0.15:
        parts.append("WKST=" + rng.choice(["MO", "SU", "WE"]))
    if rng.random() < 0.2:
        parts.append("BYSETPOS=" + str(rng.choice([1, 2, -1, -2])))
    return ";".join(parts)

def val(name, freq, rng):
    r = rng
    if name == "BYMONTH":
        return ",".join(str(x) for x in sorted(r.sample(range(1, 13), r.randint(1, 2))))
    if name == "BYMONTHDAY":
        return ",".join(str(x) for x in r.sample([1, 5, 15, 28, 29, 30, 31, -1, -2, -5], r.randint(1, 2)))
    if name == "BYYEARDAY":
        return ",".join(str(x) for x in r.sample([1, 60, 100, 200, 365, 366, -1, -60], r.randint(1, 2)))
    if name == "BYWEEKNO":
        return ",".join(str(x) for x in r.sample([1, 2, 20, 52, 53, -1, -2], r.randint(1, 2)))
    if name == "BYDAY":
        days = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
        if freq in ("MONTHLY", "YEARLY") and r.random() < 0.5:
            return ",".join(r.choice(["1", "2", "3", "-1", "-2"]) + r.choice(days)
                            for _ in range(r.randint(1, 2)))
        return ",".join(sorted(r.sample(days, r.randint(1, 3))))
    raise ValueError(name)

def fmt(v):
    return [x.strftime("%Y-%m-%dT%H:%M") for x in v][:6]


if __name__ == "__main__":
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    seen, diffs = set(), []
    for _ in range(n):
        rule = gen(rng)
        ds = rng.choice(DTSTARTS)
        key = (rule, ds)
        if key in seen:
            continue
        seen.add(key)
        d = compare(rule, ds)
        if d:
            diffs.append((rule, ds, d[0], d[1]))
    print("cases=%d divergent=%d" % (len(seen), len(diffs)))
    for rule, ds, mine, theirs in diffs[:40]:
        print("\n--- %s  DTSTART=%s" % (rule, ds.isoformat()))
        print("  naive   :", fmt(mine) if not isinstance(mine, str) else mine)
        print("  dateutil:", fmt(theirs) if not isinstance(theirs, str) else theirs)


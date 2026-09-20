"""What is HORIZON_DAYS buying, and what does it cost? (finding 064)

`src/differ.py`'s HORIZON_DAYS has been 365*30+8 since the corpus was first
built and nothing had ever justified the number. This script asks the two
questions separately, because they want different measurement conditions.

    python3 tools/cost_horizon.py value --days 21916 36525 109575
    python3 tools/cost_horizon.py cost  --days 10958 109575

VALUE re-expands every horizon-bounded case at a longer horizon and reports how
many reach the occurrence cap, how many merely gain occurrences, how many gain
a *first* occurrence, whether any existing prefix CHANGES, and whether the
naive/dateutil corroboration still holds out there. It runs in parallel: only
correctness is being measured and correctness does not care about load.

COST is serial and single-process, because a timing taken under N-way load is
not a cost (standing rule 47). It splits each case into the two halves
`compare()` actually runs -- the naive expander, which the horizon bounds, and
dateutil, which it does not, because `compare()` filters dateutil's output to
the horizon *after the fact* instead of bounding its search.
"""
import sys, os, json, time, argparse
from datetime import datetime, timedelta
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import env; env.add_dateutil_to_path()
import naive
from differ import du_expand

N = 8
FMT = "%Y%m%dT%H%M%S"


def load(bound="horizon"):
    cases = json.load(open(os.path.join(ROOT, "corpus", "corroborated.json")))["cases"]
    return [c for c in cases if bound == "all" or c["expect_bound"] == bound]


def _one(arg):
    rule, ds_s, base, days = arg
    ds = datetime.strptime(ds_s, FMT)
    horizon = ds + timedelta(days=days)
    try:
        mine = naive.expand(rule, ds, horizon=horizon, limit=N)[:N]
    except Exception as e:
        return {"rrule": rule, "dtstart": ds_s, "err": "naive:" + type(e).__name__}
    theirs = du_expand(rule, ds, N)
    if isinstance(theirs, str):
        return {"rrule": rule, "dtstart": ds_s, "err": theirs}
    mine = [x.strftime(FMT) for x in mine if x <= horizon][:N]
    theirs = [x.strftime(FMT) for x in theirs if x <= horizon][:N]
    return {"rrule": rule, "dtstart": ds_s, "base": base, "new": mine,
            "agree": mine == theirs, "dateutil": None if mine == theirs else theirs}


def value(a):
    cases = load(a.bound)
    print("horizon-bounded cases: %d" % len(cases))
    for days in a.days:
        args = [(c["rrule"], c["dtstart"], c["expect"], days) for c in cases]
        t0 = time.time()
        with Pool(a.procs) as p:
            rows = p.map(_one, args, chunksize=4)
        ok = [r for r in rows if "err" not in r]
        print("days=%-7d n=%-4d err=%-2d disagree=%-2d reach_cap=%-4d extended=%-4d "
              "first_occurrence=%-3d PREFIX_CHANGED=%-3d  (%.0fs, parallel: not a cost)"
              % (days, len(rows), len(rows) - len(ok),
                 sum(1 for r in ok if not r["agree"]),
                 sum(1 for r in ok if len(r["new"]) >= N),
                 sum(1 for r in ok if len(r["new"]) > len(r["base"])),
                 sum(1 for r in ok if not r["base"] and r["new"]),
                 sum(1 for r in ok if r["new"][:len(r["base"])] != r["base"]),
                 time.time() - t0))
        if a.out:
            json.dump(rows, open("%s.%d.json" % (a.out, days), "w"), indent=1)


def cost(a):
    cases = load(a.bound)
    print("cases: %d (%d with an empty `expect`)"
          % (len(cases), sum(1 for c in cases if not c["expect"])))
    t0 = time.time()
    du_empty = du_rest = 0.0
    for c in cases:
        ds = datetime.strptime(c["dtstart"], FMT)
        t = time.time(); du_expand(c["rrule"], ds, N); d = time.time() - t
        if c["expect"]: du_rest += d
        else: du_empty += d
    print("dateutil half (HORIZON-INDEPENDENT): %6.2fs total  %6.2fs on empty-`expect` "
          "cases  %.2fs on the rest" % (time.time() - t0, du_empty, du_rest))
    for days in a.days:
        t0 = time.time(); emp = rest = 0.0
        for c in cases:
            ds = datetime.strptime(c["dtstart"], FMT)
            t = time.time()
            naive.expand(c["rrule"], ds, horizon=ds + timedelta(days=days), limit=N)
            d = time.time() - t
            if c["expect"]: rest += d
            else: emp += d
        print("naive half @ %7dd:                %6.2fs total  %6.2fs empty  %.2fs rest"
              % (days, time.time() - t0, emp, rest))


ap = argparse.ArgumentParser()
ap.add_argument("mode", choices=["value", "cost"])
ap.add_argument("--days", type=int, nargs="+", default=[21916, 36525, 109575])
ap.add_argument("--bound", default="horizon")
ap.add_argument("--procs", type=int, default=6)
ap.add_argument("--out", default=None)
a = ap.parse_args()
(value if a.mode == "value" else cost)(a)

#!/usr/bin/env python3
"""124: what the twenty cases between 10s and 20s are paying for.

  python3 findings/repro/124-what-makes-dtical-slow.py          # ~12 min
  python3 findings/repro/124-what-makes-dtical-slow.py --check  # same, diffs
                                                               # the stored
                                                               # classification

Finding 122 measured every case's wall time against `DateTime::Event::ICal` and
left the band between 10s and 20s unexplained: the 34 cases pinned at the alarm
are accounted for by the refusals and loops of findings 029 and 047, and the
twenty below them were not accounted for by anything.

THREE MEASUREMENTS, IN THE ORDER THAT MADE THEM NECESSARY.

(1) SCALING IN `limit`.  Four cases spanning the bands, timed at limit 1..25.
    This is here to rule out the obvious wrong mechanism -- a re-expansion from
    DTSTART for every occurrence, which would be quadratic.  It is not: every
    case is a fixed cost plus a CONSTANT cost per occurrence, so the question
    becomes what sets the per-occurrence cost.

(2) A CONTROLLED GRID over synthetic rules: three frequencies x seven
    restrictions x BYSETPOS present or absent, every other field held fixed.
    Synthetic on purpose -- the corpus cannot vary one part at a time, and a
    predictor fitted to the corpus labels could not then be tested on them.

(3) AN ABLATION ON THE REAL POPULATION: every corpus case finding 122 timed at
    or above the floor, re-run with the part the grid implicates DELETED, at the
    same limit.  This is a PERFORMANCE ablation and NOT a correctness one --
    deleting BYSETPOS changes the answer, and no occurrence compared here is
    claimed to be right.  What it tests is whether the grid's mechanism is the
    one the real slow cases are actually paying for.

WHAT IS STORED AND WHAT IS NOT.  Wall times are PRINTED, never stored: the
standing rule from finding 183's wake is that findings/data/* is the pool the
provenance audit searches, and an incidental millisecond left there can silently
back another finding's declared-unbacked figure.  The stored artifact holds only
the structural result -- each case's class, and whether the ablation moved it
below the floor -- which is what `--check` can compare without re-litigating the
load on the machine.
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CASES = os.path.join(REPO, "conformance", "cases.ndjson")
TIMES = os.path.join(REPO, "findings", "data", "122-dtical-case-times.json")
OUT = os.path.join(REPO, "findings", "data", "124-dtical-cost-classes.json")
ADAPTER = os.path.join(REPO, "conformance", "adapters", "perl",
                       "dtical_adapter.pl")
# The grid's deadline. Long enough that no cell the grid cares about is clipped,
# short enough that the one cell which does not terminate cannot stall the run.
GRID_DEADLINE = 90
# finding 122's floor: the time below which a case was not individually recorded.
FLOOR_S = 5.0

# The period's OWN part -- the one BY part whose values are a sub-unit of the
# frequency's period and so cannot make a candidate rare within it.
NATURAL = {"DAILY": None, "WEEKLY": "BYDAY", "MONTHLY": "BYMONTHDAY",
           "YEARLY": "BYMONTH"}
# The parts that narrow WHICH candidate dates survive, as opposed to which
# clock times. BYHOUR/BYMINUTE/BYSECOND multiply a day's candidates; they do not
# make a day rare, and the grid holds them absent throughout.
DATE_PARTS = ("BYMONTH", "BYMONTHDAY", "BYDAY", "BYYEARDAY", "BYWEEKNO")


def parts(rrule):
    return dict(p.split("=", 1) for p in rrule.split(";") if "=" in p)


def unparse(d):
    return ";".join("%s=%s" % kv for kv in d.items())


def run(rrule, dtstart, limit, deadline):
    """One case, one process. Returns (seconds, n_occurrences, error-or-None)."""
    case = {"id": "probe", "dtstart": dtstart, "rrule": rrule, "limit": limit}
    env = dict(os.environ, RRULE_CASE_TIMEOUT=str(deadline))
    t = time.time()
    p = subprocess.run(["perl", ADAPTER], input=json.dumps(case) + "\n",
                       capture_output=True, text=True, env=env)
    el = time.time() - t
    try:
        r = json.loads(p.stdout.splitlines()[0])
    except Exception:
        return el, None, (p.stderr or "no reply").strip().splitlines()[0][:70]
    return el, len(r.get("occurrences") or []), r.get("error")


def classify(rrule):
    """The grid's mechanism, as a predicate over a rule, decided WITHOUT
    reference to any measured time.

    Two shapes are expensive, and they are the same shape twice: a candidate
    that is RARE inside the period the library steps through.

      'bysetpos'    BYSETPOS is present and some date part other than the
                    period's own narrows the candidate set. BYSETPOS has to
                    select from a materialised set, so the whole period must be
                    built before anything can be returned.
      'conjunction' two independent date parts are both present with no
                    BYSETPOS. Their intersection is rarer than either.
      'cheap'       neither.
    """
    r = parts(rrule)
    freq = r.get("FREQ", "DAILY")
    present = [p for p in DATE_PARTS if p in r]
    narrowing = [p for p in present if p != NATURAL.get(freq)]
    if "BYSETPOS" in r:
        return "bysetpos" if narrowing else "cheap"
    return "conjunction" if len(present) >= 2 else "cheap"


def ablate(rrule):
    """Delete the part the class blames, leaving the rest of the rule alone."""
    r = parts(rrule)
    cls = classify(rrule)
    if cls == "bysetpos":
        r.pop("BYSETPOS")
    elif cls == "conjunction":
        freq = r.get("FREQ", "DAILY")
        # Drop the LAST narrowing part, keeping the period's own, so the rule
        # stays a rule of the same frequency rather than becoming unrestricted.
        drop = [p for p in DATE_PARTS if p in r and p != NATURAL.get(freq)]
        if not drop:
            return None
        r.pop(drop[-1])
    else:
        return None
    return unparse(r)


def scaling(cases, out):
    out("\n(1) SCALING IN `limit` -- is the per-occurrence cost constant?\n")
    probe = ["88d38e1b367e", "35dd408087d4", "b9db1bd13b63", "c4b654abc6ee"]
    for cid in probe:
        base = cases[cid]
        out("  %s  %s" % (cid, base["rrule"]))
        prev = None
        for L in (1, 2, 3, 5, 8, 13, 20, 25):
            el, n, _ = run(base["rrule"], base["dtstart"], L, 300)
            d = "" if prev is None else "   +%6.2f" % (el - prev)
            out("    limit=%-3d %8.2fs  n=%-3s%s" % (L, el, n, d))
            prev = el
            if el > 120:
                out("    (abandoned above 120s -- the trend is already decided)")
                break


def grid(out):
    out("\n(2) THE CONTROLLED GRID -- limit 3, dtstart 20260805T090000, "
        "deadline %ds\n" % GRID_DEADLINE)
    dtstart = "20260805T090000"
    shapes = ["", "BYMONTH=4", "BYMONTHDAY=5", "BYDAY=WE",
              "BYMONTHDAY=5;BYDAY=WE", "BYMONTH=4;BYMONTHDAY=29",
              "BYMONTH=4;BYDAY=WE"]
    worst = {"": 0.0, ";BYSETPOS=-1": 0.0}
    for freq in ("DAILY", "WEEKLY", "MONTHLY"):
        out("  FREQ=%s" % freq)
        out("    %-26s %14s %14s" % ("restriction", "no BYSETPOS",
                                     "BYSETPOS=-1"))
        for shape in shapes:
            cells = []
            for sp in ("", ";BYSETPOS=-1"):
                rrule = "FREQ=" + freq + (";" + shape if shape else "") + sp
                el, n, err = run(rrule, dtstart, 3, GRID_DEADLINE)
                worst[sp] = max(worst[sp], el)
                cells.append("%7.2fs n=%s%s" % (el, n, "!" if err else ""))
            out("    %-26s %14s %14s" % (shape or "(none)", cells[0], cells[1]))
    out("\n  worst cell without BYSETPOS: %6.2fs" % worst[""])
    out("  worst cell with    BYSETPOS: %6.2fs" % worst[";BYSETPOS=-1"])
    return worst


def ablation(cases, times, out):
    out("\n(3) THE ABLATION ON THE REAL POPULATION -- every case finding 122\n"
        "    timed at or above its %.0fs floor, re-run with the part its class\n"
        "    blames deleted, at the case's own limit.\n" % FLOOR_S)
    rows = []
    for cid, ms in sorted(times.items(), key=lambda kv: -kv[1]):
        c = cases[cid]
        cls = classify(c["rrule"])
        ab = ablate(c["rrule"])
        if ab is None:
            rows.append({"id": cid, "class": cls, "ablated": None,
                         "below_floor": None})
            continue
        el, n, err = run(ab, c["dtstart"], c["limit"], GRID_DEADLINE)
        # An ablated rule that DIES is fast and says nothing about cost: this
        # library kills an empty intersection in ~0.1s at Recurrence.pm:822
        # (findings 035, 094). Counting that as "the ablation made it cheap"
        # would let a crash stand in for a speedup, so DIED is its own outcome
        # and is NOT counted as below_floor. Audited at wake 189; 5 of these
        # 71 were being scored as speedups.
        outcome = "died" if err else ("faster" if el < FLOOR_S else "still_slow")
        rows.append({"id": cid, "class": cls, "ablated": ab,
                     "below_floor": outcome == "faster", "outcome": outcome})
        out("    %s %-11s %6.0fms -> %7.2fs %-10s %s"
            % (cid, cls, ms, el,
               {"faster": "OK", "still_slow": "STILL", "died": "DIED(822)"}[outcome],
               ab if len(ab) < 56 else ab[:53] + "..."))
    return rows


def summarise(rows, times, out):
    import collections
    by = collections.Counter(r["class"] for r in rows)
    out("\n  classes among the %d cases at or above the floor: %s"
        % (len(rows), ", ".join("%s=%d" % kv for kv in sorted(by.items()))))
    for cls in sorted(by):
        sub = [r for r in rows if r["class"] == cls and r["ablated"]]
        if not sub:
            continue
        ok = sum(1 for r in sub if r["outcome"] == "faster")
        died = sum(1 for r in sub if r["outcome"] == "died")
        out("  %-11s ablated %3d, genuinely faster %3d, died at 822 %3d, "
            "still slow %3d" % (cls, len(sub), ok, died, len(sub) - ok - died))
    died_all = [r["id"] for r in rows if r.get("outcome") == "died"]
    out("  ablations that fell below the floor BY DYING (no cost evidence): "
        "%d%s" % (len(died_all), (" -- " + " ".join(sorted(died_all)))
                  if died_all else ""))
    unexplained = [r["id"] for r in rows if r["class"] == "cheap"]
    out("  cases the predicate calls cheap and the clock calls slow: %d%s"
        % (len(unexplained), (" -- " + " ".join(unexplained))
           if unexplained else ""))
    return unexplained


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="re-measure and diff the stored classification")
    ap.add_argument("--skip-scaling", action="store_true")
    a = ap.parse_args(argv)
    lines = []

    def out(s=""):
        print(s)
        sys.stdout.flush()
        lines.append(s)

    cases = {}
    for line in open(CASES):
        c = json.loads(line)
        cases[c["id"]] = c
    times = {d["id"]: d["ms"]
             for d in json.load(open(TIMES))["slow"]}
    out("cases: %d   timed at or above the floor by finding 122: %d"
        % (len(cases), len(times)))

    if not a.skip_scaling:
        scaling(cases, out)
    grid(out)
    rows = ablation(cases, times, out)
    unexplained = summarise(rows, times, out)

    # The whole-corpus side of the predicate: it must not call a case expensive
    # that the clock called fast, or it is describing nothing.
    fp = [cid for cid, c in cases.items()
          if cid not in times and classify(c["rrule"]) != "cheap"]
    out("\n  cases the predicate calls expensive and the clock called fast: "
        "%d of %d" % (len(fp), len(cases) - len(times)))
    out("  -- the predicate is NECESSARY-side only: it names the mechanism a\n"
        "     slow case pays for, and does NOT claim every rule of that shape\n"
        "     is slow. How rare the candidate is still sets the cost.")

    result = {"floor_s": FLOOR_S, "grid_deadline": GRID_DEADLINE,
              "ablated_died": sorted(r["id"] for r in rows
                                     if r.get("outcome") == "died"),
              "classes": {r["id"]: r["class"] for r in rows},
              "ablated_below_floor": {r["id"]: r["below_floor"]
                                      for r in rows if r["ablated"]},
              "ablated_outcome": {r["id"]: r["outcome"]
                                  for r in rows if r["ablated"]},
              "unexplained": sorted(unexplained),
              "predicate_expensive_among_fast": len(fp)}
    if a.check:
        old = json.load(open(OUT))
        bad = []
        for k in ("classes", "unexplained", "predicate_expensive_among_fast",
                  "ablated_died"):
            if old.get(k) != result[k]:
                bad.append(k)
        # below_floor is a timing call and may legitimately move under load;
        # report drift without failing on it.
        moved = [k for k, v in result["ablated_below_floor"].items()
                 if old.get("ablated_below_floor", {}).get(k) != v]
        out("\n--check: structural drift in %s" % (bad or "nothing"))
        out("--check: ablation verdict moved for %d case(s)%s"
            % (len(moved), (": " + " ".join(sorted(moved))) if moved else ""))
        return 1 if bad else 0
    json.dump(result, open(OUT, "w"), indent=1, sort_keys=True)
    out("\nwrote %s" % os.path.relpath(OUT, REPO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

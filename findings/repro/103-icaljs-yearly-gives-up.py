#!/usr/bin/env python3
"""103 -- ical.js: a FREQ=YEARLY expansion silently ENDS after 28 consecutive
non-matching iterations, and the Gregorian calendar produces runs longer than 28.

Default mode is READ-ONLY and ADAPTER-FREE: it replays the adapter answers
stored in findings/data/103-*.json and re-derives the corpus scope from
conformance/cases.ndjson. It stamps the repository's own cases_id and REFUSES
if the corpus has moved (rule 94).

  python3 findings/repro/103-icaljs-yearly-gives-up.py
  python3 findings/repro/103-icaljs-yearly-gives-up.py --run-adapters
      # needs node, python3, java, php; WRITES findings/data/103-*.json

WHAT THIS ESTABLISHES
  D  the defect, as a PREDICTOR, not a description: ical.js's answer equals the
     reference answer CUT at the first point where the iterator would have to
     pass 28 consecutive non-matching iterations to reach the next occurrence.
     Exact, not approximate, on every probe.
  A  the ASYMMETRY that makes it a defect rather than a documented limit:
     init() searches for the FIRST occurrence with no such bound at all (it
     scans to year 20000), so the same rule answers or truncates depending on
     where DTSTART sits relative to the gap.
  C  controls the predictor must NOT fire on: the same rule from a DTSTART past
     the gap, an INTERVAL that shortens the run below the bound, a rule with no
     leap/weekday conjunction, and the MONTHLY analogue whose own 336 bound is
     never reached.
  S  scope, stated against the defect rather than for it: 0 of the corpus's 373
     FREQ=YEARLY cases can reach the bound. This finding moves NO score and
     subtracts NOTHING from 074's residual.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(HERE, "findings", "data", "103-icaljs-yearly-gives-up.json")
TIMEOUT_MS = "45000"
BOUND = 28   # recur_iterator.js line 440: `else if (++invalid_count == 28)`

ADAPTERS = [
    ("dateutil",  ["python3", "conformance/adapters/dateutil_adapter.py"]),
    ("icaljs",    ["node", "conformance/adapters/icaljs_adapter.js"]),
    ("rrulejs",   ["node", "conformance/adapters/rrulejs_adapter.js"]),
    ("dmfs",      ["java", "-cp", "conformance/adapters/java/classes:conformance/adapters/java/libs/*", "DmfsAdapter"]),
    ("ical4j411", ["java", "-cp", "conformance/adapters/java/classes:conformance/adapters/java/libs/*", "Ical4jAdapter"]),
    ("sabre",     ["php", "conformance/adapters/php/vobject_adapter.php"]),
]

# (label, group, dtstart, rrule, limit, what it establishes)
#   D = the predictor fires AND ical.js is short of the reference.
#   C = the predictor must NOT fire, and ical.js must match the reference.
PROBES = [
    ("D-5mo",      "D", "20260101T090000", "FREQ=YEARLY;BYMONTH=2;BYDAY=5MO", 8,
     "a fifth Monday in February needs a leap year whose Feb 1 is a Monday: "
     "2044, 2072, then nothing until 2112. ical.js stops at 2072"),
    ("D-feb29mon", "D", "20260101T090000", "FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=29;BYDAY=MO", 8,
     "a different rule text reaching the same rare conjunction, stopped at the "
     "same year: the mechanism is the empty run, not the BYDAY ordinal"),
    ("D-count",    "D", "20260101T090000", "FREQ=YEARLY;BYMONTH=2;BYDAY=5MO;COUNT=6", 6,
     "COUNT=6 returns 2. A caller who asked for a fixed count gets a short "
     "series with no error: the loss is SILENT"),
    ("D-interval3","D", "20260101T090000", "FREQ=YEARLY;INTERVAL=3;BYMONTH=2;BYDAY=5MO", 6,
     "INTERVAL=3 keeps only 2044 -- the next reachable year is 2140, 32 "
     "iterations away. A LARGER interval truncates EARLIER in calendar terms"),
    # --- controls. The predictor must not fire and ical.js must be correct. ---
    ("A-dtstart",  "A", "20800101T090000", "FREQ=YEARLY;BYMONTH=2;BYDAY=5MO", 8,
     "DECIDING, and it is the asymmetry: the SAME rule from 2080 must cross the "
     "SAME 31 empty iterations to reach 2112 -- and it does, because that search "
     "happens in init(), which is not bounded. Past the gap it is fully correct. "
     "Bounded and unbounded search for the same thing in the same class"),
    ("C-interval2","C", "20260101T090000", "FREQ=YEARLY;INTERVAL=2;BYMONTH=2;BYDAY=5MO", 6,
     "DECIDING: INTERVAL=2 crosses the SAME 40 calendar years correctly, in 19 "
     "iterations. The bound counts ITERATIONS, not years"),
    ("C-leaponly", "C", "20260101T090000", "FREQ=YEARLY;BYYEARDAY=366", 8,
     "leap years alone, via BYYEARDAY=366 rather than BYMONTHDAY=29 (which "
     "finding 101 already shows ical.js mishandles): gaps of at most 8, no loss"),
    ("C-monthly",  "C", "20260101T090000", "FREQ=MONTHLY;BYMONTH=2;BYMONTHDAY=29;BYDAY=MO", 6,
     "the MONTHLY analogue of the identical conjunction is CORRECT. Its own "
     "bound is 336, and BYMONTH is a contracting rule checked outside "
     "next_month(), so invalid_count is reset every month. FREQ=YEARLY is "
     "load-bearing"),
]


def parts(rrule):
    return dict(p.split("=", 1) for p in rrule.split(";") if "=" in p)


def interval(rrule):
    m = re.search(r"INTERVAL=(\d+)", rrule)
    return int(m.group(1)) if m else 1


def empty_runs(years, iv):
    """Consecutive NON-matching iterations BETWEEN matching years. The run from
    DTSTART to the first match is excluded: init() is not bounded."""
    out = []
    for a, b in zip(years, years[1:]):
        out.append(max(0, (b - a) // iv - 1))
    return out


def predict(dtstart, rrule, occurrences):
    """THE PREDICTOR. Cut the reference answer at the first occurrence the
    iterator cannot reach without BOUND consecutive non-matching iterations."""
    if occurrences is None:
        return None
    if parts(rrule).get("FREQ") != "YEARLY":
        return {"occurrences": occurrences}   # the bound is per-frequency
    iv = interval(rrule)
    prev, kept = None, []
    for o in occurrences:
        y = int(o[:4])
        # prev is None for the FIRST occurrence: init() finds it with no bound.
        if prev is not None and y != prev and (y - prev) // iv - 1 >= BOUND:
            break
        kept.append(o)
        prev = y
    return {"occurrences": kept}


def fires(dtstart, rrule, occurrences):
    return predict(dtstart, rrule, occurrences) != {"occurrences": occurrences}


def run(cmd, rows):
    env = dict(os.environ, RRULE_CASE_TIMEOUT_MS=TIMEOUT_MS)
    inp = "\n".join(json.dumps(r) for r in rows)
    p = subprocess.run(cmd, input=inp, capture_output=True, text=True, cwd=HERE, env=env)
    out = {}
    for line in p.stdout.splitlines():
        if not line.startswith("{"):
            continue
        o = json.loads(line)
        out[o["id"]] = {"error": o["error"]} if "error" in o else {"occurrences": o.get("occurrences")}
    return out


def cases_id():
    """The repository's OWN cases_id. Never re-hash cases.ndjson (096's near-miss)."""
    sys.path.insert(0, os.path.join(HERE, "tools"))
    import corpus_id
    return corpus_id.compute()["cases_id"]


def load_cases():
    return [json.loads(l) for l in
            open(os.path.join(HERE, "conformance", "cases.ndjson"))]


def corpus_reach(cases):
    """S: how close does the corpus get to the bound? Measured from each case's
    OWN stored reference expansion, so no adapter is needed."""
    worst = []
    for c in cases:
        if parts(c["rrule"]).get("FREQ") != "YEARLY":
            continue
        iv = interval(c["rrule"])
        years = sorted({int(s[:4]) for s in c.get("expect", [])})
        runs = empty_runs(years, iv) or [0]
        worst.append((max(runs), c["id"], iv, c["rrule"]))
    worst.sort(reverse=True)
    return worst


def show(v, n=4):
    if v is None:
        return "no answer line"
    if "error" in v:
        return "REJECTED: " + v["error"]
    o = v["occurrences"]
    return "(empty)" if o == [] else " ".join(x[:8] for x in o[:n]) + (" ..." if len(o) > n else "")


def main():
    os.chdir(HERE)
    cases = load_cases()
    rows = [{"id": l, "dtstart": d, "rrule": r, "limit": n} for l, _, d, r, n, _ in PROBES]
    stored = json.load(open(DATA)) if os.path.exists(DATA) else {}

    if "--run-adapters" in sys.argv:
        table = {}
        for name, cmd in ADAPTERS:
            got = run(cmd, rows)
            if got:
                table[name] = got
            else:
                print("  (%s produced nothing, skipped)" % name)
        stored = {"cases_id": cases_id(),
                  "adapter_case_timeout_ms": int(TIMEOUT_MS),
                  "bound": BOUND,
                  "icaljs_version": "2.2.1",
                  "probes": {l: {"group": g, "dtstart": d, "rrule": r,
                                 "limit": n, "note": t}
                             for l, g, d, r, n, t in PROBES},
                  "adapters": table}
        json.dump(stored, open(DATA, "w"), indent=1, sort_keys=True)
        print("-> %s" % DATA)

    if not stored:
        sys.exit("no stored answers; run once with --run-adapters")
    if stored.get("cases_id") != cases_id():
        sys.exit("REFUSING: stored answers were taken at cases_id %s, corpus is now %s. "
                 "Re-run with --run-adapters." % (str(stored.get("cases_id"))[:12], cases_id()[:12]))

    t = stored["adapters"]
    ic, du = t["icaljs"], t["dateutil"]
    print("103 -- ical.js %s: FREQ=YEARLY ends after %d consecutive non-matching iterations"
          % (stored["icaljs_version"], stored["bound"]))
    print("cases_id %s ; adapter case timeout %d ms" % (cases_id()[:12], stored["adapter_case_timeout_ms"]))
    print("PREDICTOR: ical.js(rule) == reference(rule) cut before the first occurrence")
    print("           that is >= %d non-matching iterations past the PREVIOUS ONE." % BOUND)
    print("           The gap from DTSTART to the FIRST occurrence is exempt: init()")
    print("           scans to year 20000 unbounded. That asymmetry is the defect.")

    bad = []
    print("\n-- D: the predictor fires, and ical.js is short of the reference.")
    for l, g, d, r, n, note in PROBES:
        if g != "D":
            continue
        ref = du.get(l, {}).get("occurrences")
        ok = ic.get(l) == predict(d, r, ref)
        differs = ic.get(l) != du.get(l)
        fired = fires(d, r, ref)
        print("  %-12s %s" % (l, "PREDICTED" if (ok and differs and fired) else "*** MISS ***"))
        print("     %s  (%s)" % (r, note))
        print("     ical.js   %s" % show(ic.get(l)))
        print("     reference %s" % show(du.get(l)))
        if not (ok and differs and fired):
            bad.append(l)

    print("\n-- A / C: the predictor does NOT fire, and ical.js is correct.")
    for l, g, d, r, n, note in PROBES:
        if g not in ("A", "C"):
            continue
        ref = du.get(l, {}).get("occurrences")
        fired = fires(d, r, ref)
        agrees = ic.get(l) == du.get(l)
        print("  %-12s %s" % (l, ("HELD" if g == "C" else "ASYMMETRY SHOWN")
                                  if (agrees and not fired) else "*** MISS ***"))
        print("     %s  (%s)" % (r, note))
        print("     ical.js   %s" % show(ic.get(l)))
        if not (agrees and not fired):
            bad.append(l)

    print("\n-- the other implementations on D-5mo (is ical.js alone?)")
    for name in [n for n, _ in ADAPTERS]:
        if name not in t:
            continue
        v = t[name].get("D-5mo")
        same = "== reference" if v == du.get("D-5mo") else "DIFFERS"
        print("  %-10s %-12s %s" % (name, same, show(v, 3)))
    print("  sabre differs by prepending DTSTART; that is its own separate reading,")
    print("  not this defect -- its tail reaches 2112 and beyond.")

    worst = corpus_reach(cases)
    print("\n-- S: scope. Longest run of non-matching iterations any corpus")
    print("   FREQ=YEARLY case demands, from its own stored reference expansion:")
    for run_len, cid, iv, r in worst[:3]:
        print("     %2d  %s  INTERVAL=%d  %s" % (run_len, cid, iv, r))
    print("   %d YEARLY cases; longest run %d; bound %d. %d case(s) reach the bound."
          % (len(worst), worst[0][0], BOUND, sum(1 for w in worst if w[0] >= BOUND)))
    print("   This finding therefore moves NO score and subtracts NOTHING from")
    print("   074's residual. It was found by reading next(), not by measuring.")

    if bad:
        sys.exit("\nFAILED: " + ", ".join(bad))
    print("\nAll probes and controls behaved as published.")


if __name__ == "__main__":
    main()

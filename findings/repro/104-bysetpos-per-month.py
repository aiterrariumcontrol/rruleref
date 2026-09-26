#!/usr/bin/env python3
"""104 -- ical.js: at FREQ=YEARLY with a multi-valued BYMONTH and a BYDAY-derived
day set, BYSETPOS selects within EACH MONTH separately instead of within the
yearly period.

Default mode is READ-ONLY and ADAPTER-FREE: it replays the adapter answers
stored in findings/data/104-*.json. It stamps the repository's own cases_id and
REFUSES if the corpus has moved (rule 94).

  python3 findings/repro/104-bysetpos-per-month.py
  python3 findings/repro/104-bysetpos-per-month.py --run-adapters
      # needs node and python3; WRITES findings/data/104-*.json

WHAT THIS ESTABLISHES
  D  the defect, as a PREDICTOR, not a description: ical.js's answer to a rule
     with BYMONTH=m1,m2,... equals the sorted MERGE of the reference answers to
     the same rule with BYMONTH cut to each single month in turn. Exact.
  C  controls the predictor must fail or the claim is vacuous: a single-valued
     BYMONTH (per-month and per-year coincide), a day set from BYMONTHDAY rather
     than BYDAY (BYSETPOS is dropped outright -- 074's defect E), no BYMONTH at
     all (also dropped outright), and FREQ=MONTHLY.
  R  residual: this attributes 2 of the 3 ids 102 published, taking 074's
     residual to 1. The third, d27c58ae379a, is FREQ=MONTHLY and is NOT this
     defect; it stays unattributed and this finding does not claim it.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(HERE, "findings", "data", "104-bysetpos-per-month.json")
TIMEOUT_MS = "20000"

ADAPTERS = [
    ("dateutil", ["python3", "conformance/adapters/dateutil_adapter.py"]),
    ("icaljs",   ["node", "conformance/adapters/icaljs_adapter.js"]),
    ("rrulejs",  ["node", "conformance/adapters/rrulejs_adapter.js"]),
    ("dmfs",     ["java", "-cp", "conformance/adapters/java/classes:conformance/adapters/java/libs/*", "DmfsAdapter"]),
]

# The two residual ids this finding claims. Both are in 074's base set; the
# ledger in repro/102-residual-ledger.py re-checks that on every run.
CLAIMED = ["7a6256afbb5b", "f9f6ec0cf765"]

# (label, group, dtstart, rrule, limit, what it establishes)
PROBES = [
    ("D-pos2",   "D", "20270101T090000", "FREQ=YEARLY;BYMONTH=9,11;BYDAY=WE;BYSETPOS=2", 6,
     "the second Wednesday of the YEAR's Sep+Nov set is one date; ical.js "
     "returns two, one per month"),
    ("D-neg1",   "D", "20270101T090000", "FREQ=YEARLY;BYMONTH=9,11;BYDAY=WE;BYSETPOS=-1", 6,
     "negative positions too: the last Wednesday of each month, not of the year"),
    ("D-pos5",   "D", "20270101T090000", "FREQ=YEARLY;BYMONTH=9,11;BYDAY=WE;BYSETPOS=5", 6,
     "DECIDING: BYSETPOS=5 overruns a 4-Wednesday month, so the years that "
     "produce an occurrence at all differ. ical.js keeps 2027 (Sep has five) "
     "and 2028 (Nov has five) and drops 2029-2031; the reference keeps every "
     "year, because the year's set always has at least eight. Not a shift "
     "in the dates -- a different SET of years"),
    ("D-twoday", "D", "20270101T090000", "FREQ=YEARLY;BYMONTH=3,9;BYDAY=TU,TH;BYSETPOS=-2", 6,
     "two weekdays and two distant months: still one pick per month"),
    ("D-case1",  "D", "20260728T090000", "FREQ=YEARLY;INTERVAL=4;BYMONTH=7,8;BYDAY=-1TU,-2WE;WKST=WE;BYSETPOS=2", 25,
     "corpus case 7a6256afbb5b, on 074's residual, with INTERVAL=4 and WKST"),
    ("D-case2",  "D", "20270908T090000", "FREQ=YEARLY;BYMONTH=9,11;BYDAY=WE;BYSETPOS=2", 25,
     "corpus case f9f6ec0cf765, on 074's residual"),
    # --- controls. The predictor MUST FAIL these. ---
    ("C-onemonth", "C", "20270101T090000", "FREQ=YEARLY;BYMONTH=9;BYDAY=WE;BYSETPOS=2", 5,
     "a SINGLE-valued BYMONTH is correct -- per-month and per-year coincide, so "
     "there is nothing to get wrong. Multi-valued BYMONTH is load-bearing"),
    ("C-nomonth",  "C", "20270101T090000", "FREQ=YEARLY;BYDAY=WE;BYSETPOS=2", 5,
     "with NO BYMONTH, BYSETPOS is dropped outright: every Wednesday is "
     "returned. A different symptom, not a per-month split"),
    ("C-monthday", "C", "20270101T090000", "FREQ=YEARLY;BYMONTH=9,11;BYMONTHDAY=1,2,3,4,5;BYSETPOS=2", 5,
     "the same two months with the day set from BYMONTHDAY: BYSETPOS dropped "
     "outright (074's defect E). BYDAY is load-bearing"),
    ("C-monthly",  "C", "20270101T090000", "FREQ=MONTHLY;BYDAY=WE;BYSETPOS=2", 5,
     "FREQ=MONTHLY is correct from the second period on; its first period is "
     "finding 004's separate defect, not this one"),
]


def parts(rrule):
    return dict(p.split("=", 1) for p in rrule.split(";") if "=" in p)


def split_months(rrule):
    """One rule per BYMONTH value, everything else unchanged."""
    months = parts(rrule).get("BYMONTH", "").split(",")
    if len(months) < 2:
        return None
    return [re.sub(r"BYMONTH=[0-9,]+", "BYMONTH=" + m, rrule) for m in months]


def predict(ref_by_rule, dtstart, rrule, limit):
    """THE PREDICTOR. Merge the reference answers to the single-month rules."""
    subs = split_months(rrule)
    if subs is None:
        return None
    merged = []
    for s in subs:
        o = ref_by_rule.get(s)
        if o is None:
            return None
        merged += o
    return {"occurrences": sorted(merged)[:limit]}


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
    sys.path.insert(0, os.path.join(HERE, "tools"))
    import corpus_id
    return corpus_id.compute()["cases_id"]


def rows_for_probes():
    """Each probe as written, plus each of its single-month splits. The splits
    are asked with a LARGER limit: a merge of two lists truncated to N cannot be
    trusted to reproduce the first N of the merge."""
    rows = []
    for l, _, d, r, n, _ in PROBES:
        rows.append({"id": l, "dtstart": d, "rrule": r, "limit": n})
        for k, s in enumerate(split_months(r) or []):
            rows.append({"id": "%s#%d" % (l, k), "dtstart": d, "rrule": s, "limit": n})
    return rows


def show(v, n=4):
    if v is None:
        return "no answer line"
    if "error" in v:
        return "REJECTED: " + v["error"]
    o = v["occurrences"]
    return "(empty)" if o == [] else " ".join(x[:8] for x in o[:n]) + (" ..." if len(o) > n else "")


def main():
    os.chdir(HERE)
    rows = rows_for_probes()
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
                  "claimed_residual_ids": CLAIMED,
                  "probes": {l: {"group": g, "dtstart": d, "rrule": r,
                                 "limit": n, "splits": split_months(r), "note": t}
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
    print("104 -- ical.js: FREQ=YEARLY + multi-valued BYMONTH + BYDAY -> BYSETPOS applied PER MONTH")
    print("cases_id %s ; adapter case timeout %d ms" % (cases_id()[:12], stored["adapter_case_timeout_ms"]))
    print("PREDICTOR: ical.js(rule) == sorted merge of reference(rule with BYMONTH cut to")
    print("           each single month), truncated to the limit")

    bad = []
    print("\n-- D: the predictor holds, and the rule as written does not.")
    for l, g, d, r, n, note in PROBES:
        if g != "D":
            continue
        ref = {stored["probes"][l]["splits"][k]: du.get("%s#%d" % (l, k), {}).get("occurrences")
               for k in range(len(stored["probes"][l]["splits"] or []))}
        p = predict(ref, d, r, n)
        ok = p is not None and ic.get(l) == p
        differs = ic.get(l) != du.get(l)
        print("  %-10s %s" % (l, "PREDICTED" if (ok and differs) else "*** MISS ***"))
        print("     %s  (%s)" % (r, note))
        print("     ical.js   %s" % show(ic.get(l)))
        print("     reference %s" % show(du.get(l)))
        if not (ok and differs):
            bad.append(l)

    print("\n-- C: the predictor does not apply or does not hold, and the reason differs each time.")
    for l, g, d, r, n, note in PROBES:
        if g != "C":
            continue
        subs = split_months(r)
        if subs is None:
            held = True          # no multi-valued BYMONTH: the predictor has nothing to say
        else:
            ref = {subs[k]: du.get("%s#%d" % (l, k), {}).get("occurrences") for k in range(len(subs))}
            held = ic.get(l) != predict(ref, d, r, n)
        print("  %-10s %s" % (l, "CONTROL HELD" if held else "*** MISS ***"))
        print("     %s  (%s)" % (r, note))
        print("     ical.js   %s" % show(ic.get(l)))
        print("     reference %s" % show(du.get(l)))
        if not held:
            bad.append(l)

    print("\n-- the other implementations on D-pos2 (is ical.js alone?)")
    for name in [n for n, _ in ADAPTERS]:
        if name not in t:
            continue
        v = t[name].get("D-pos2")
        print("  %-10s %-12s %s" % (name, "== reference" if v == du.get("D-pos2") else "DIFFERS", show(v, 3)))

    print("\n-- R: what this attributes. 102's residual was %s." % ", ".join(
        ["7a6256afbb5b", "d27c58ae379a", "f9f6ec0cf765"]))
    print("   claimed here: %s (D-case1, D-case2)" % ", ".join(CLAIMED))
    print("   NOT claimed:  d27c58ae379a -- FREQ=MONTHLY, no BYMONTH, a dropped")
    print("                 occurrence rather than a per-month split. Different defect.")
    print("   074's residual therefore goes 3 -> 1. Run repro/102-residual-ledger.py")
    print("   for the authoritative set; this line is a claim, that script is the producer.")

    if bad:
        sys.exit("\nFAILED: " + ", ".join(bad))
    print("\nAll probes and controls behaved as published.")


if __name__ == "__main__":
    main()

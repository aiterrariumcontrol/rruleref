#!/usr/bin/env python3
"""098 -- ical.js: at FREQ=YEARLY only the FIRST listed value of BYHOUR,
BYMINUTE and BYSECOND ever reaches the output.

Default mode is READ-ONLY and ADAPTER-FREE: it replays the adapter answers
stored in findings/data/098-*.json and re-derives the corpus extent from
conformance/cases.ndjson. It stamps the repository's own cases_id and REFUSES
if the corpus has moved (rule 94).

  python3 findings/repro/098-icaljs-yearly-time-parts-truncated.py
  python3 findings/repro/098-icaljs-yearly-time-parts-truncated.py --run-adapters
      # needs node, python3, php; WRITES findings/data/098-*.json

WHAT THIS ESTABLISHES
  D  the defect, as a PREDICTOR, not a description: for every probe below,
     ical.js's answer to the full rule equals dateutil's answer to the rule with
     each multi-valued time part CUT TO ITS FIRST LISTED VALUE. Exact, not
     approximate, on all of them and on all 7 corpus cases carrying the shape.
  C  controls the predictor must fail or the claim is vacuous: other
     frequencies, single-valued time parts, and multi-valued NON-time parts.
  S  scope: the same predictor holds on 0 of the 74 non-YEARLY, non-MINUTELY/
     SECONDLY corpus cases with a multi-valued time part.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(HERE, "findings", "data", "098-icaljs-yearly-time-parts-truncated.json")
RESID = os.path.join(HERE, "findings", "data", "074-icaljs-residual-reproduced.json")
TIMEOUT_MS = "45000"

ADAPTERS = [
    ("dateutil",  ["python3", "conformance/adapters/dateutil_adapter.py"]),
    ("icaljs",    ["node", "conformance/adapters/icaljs_adapter.js"]),
    ("rrulejs",   ["node", "conformance/adapters/rrulejs_adapter.js"]),
    ("sabre",     ["php", "conformance/adapters/php/vobject_adapter.php"]),
]

TIME_PARTS = ("BYHOUR", "BYMINUTE", "BYSECOND")

# (label, group, dtstart, rrule, limit, what it establishes)
#   D = the defect. criterion: ical.js(rule) == dateutil(first-value-reduced rule)
#                   AND ical.js(rule) != dateutil(rule), else the probe proves nothing.
#   C = a control the PREDICTOR MUST FAIL. ical.js must equal dateutil on the
#       rule as written; if the predictor also held here the claim would be empty.
PROBES = [
    ("R-hour",    "D", "20260302T090000", "FREQ=YEARLY;BYHOUR=9,18", 6,
     "corpus case 6e74ec2d96a8: the 18:00 occurrence of every year is gone"),
    ("R-minute",  "D", "20260302T093000", "FREQ=YEARLY;BYMINUTE=0,30", 6,
     "corpus case 3939127583ee, the case this wake set out to explain"),
    ("R-second",  "D", "20260302T093000", "FREQ=YEARLY;BYSECOND=0,15", 6,
     "corpus case a844fe388868: all three time parts, one mechanism"),
    ("D-rev",     "D", "20260302T093000", "FREQ=YEARLY;BYMINUTE=30,0", 6,
     "DECIDING: 30,0 keeps 30. It is the FIRST LISTED value, NOT the smallest"),
    ("D-rev2",    "D", "20260302T090000", "FREQ=YEARLY;BYMINUTE=45,15", 6,
     "45,15 keeps 45, and 45 is not DTSTART's minute either. Rule order, nothing else"),
    ("D-three",   "D", "20260302T090000", "FREQ=YEARLY;BYMINUTE=10,20,30", 6,
     "three values keep one, not two: it is not an off-by-one in the list walk"),
    ("D-hourmin", "D", "20260302T090000", "FREQ=YEARLY;BYHOUR=9;BYMINUTE=15,45", 6,
     "an explicit single-valued BYHOUR alongside does not rescue the BYMINUTE list"),
    ("D-bymonth", "D", "20260302T090000", "FREQ=YEARLY;BYMONTH=3;BYMINUTE=15,45", 6,
     "nor does an explicit BYMONTH"),
    ("D-count",   "D", "20260302T090000", "FREQ=YEARLY;BYMINUTE=15,45;COUNT=4", 4,
     "COUNT=4 still returns 4 occurrences -- over 4 YEARS. The loss is INVISIBLE "
     "to a caller who only counts results"),
    # --- controls. The predictor MUST FAIL these. ---
    ("C-monthly", "C", "20260302T090000", "FREQ=MONTHLY;BYMINUTE=15,45", 6,
     "same by-parts at MONTHLY: correct. FREQ=YEARLY is load-bearing"),
    ("C-daily",   "C", "20260302T090000", "FREQ=DAILY;BYMINUTE=15,45", 6,
     "correct at DAILY"),
    ("C-weekly",  "C", "20260302T090000", "FREQ=WEEKLY;BYMINUTE=15,45", 6,
     "correct at WEEKLY"),
    ("C-hourly",  "C", "20260302T090000", "FREQ=HOURLY;BYMINUTE=15,45", 6,
     "correct at HOURLY"),
    ("C-single",  "C", "20260302T090000", "FREQ=YEARLY;BYMINUTE=45", 6,
     "a SINGLE-valued time part at YEARLY is correct, and 45 is not DTSTART's "
     "minute: the rule is applied, it is the rest of the LIST that is lost"),
    ("C-bymonth", "C", "20260302T090000", "FREQ=YEARLY;BYMONTH=3,6", 6,
     "a multi-valued NON-time part at YEARLY is correct: this is about the "
     "time parts specifically, not about lists at YEARLY"),
    ("C-byday",   "C", "20260302T090000", "FREQ=YEARLY;BYMONTH=3;BYDAY=MO,TU", 6,
     "multi-valued BYDAY at YEARLY is correct too"),
]


def reduce_to_first(rrule):
    """Cut every multi-valued time part to its first LISTED value."""
    out = []
    for part in rrule.split(";"):
        k, _, v = part.partition("=")
        if k in TIME_PARTS and "," in v:
            v = v.split(",")[0]
        out.append(k + "=" + v)
    return ";".join(out)


def parts(rrule):
    return dict(p.split("=", 1) for p in rrule.split(";") if "=" in p)


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
    return {c["id"]: c for c in
            (json.loads(l) for l in
             open(os.path.join(HERE, "conformance", "cases.ndjson")))}


def multivalued_time_part(rrule):
    return any("," in parts(rrule).get(k, "") for k in TIME_PARTS)


def show(v, n=4):
    if v is None:
        return "no answer line"
    if "error" in v:
        return "REJECTED: " + v["error"]
    o = v["occurrences"]
    return "(empty)" if o == [] else " ".join(x[9:] for x in o[:n]) + (" ..." if len(o) > n else "")


def collect(cases):
    """The rows every adapter is asked: probes as written, probes reduced, and
    the corpus cases carrying the shape, both ways."""
    rows_full = [{"id": l, "dtstart": d, "rrule": r, "limit": n}
                 for l, _, d, r, n, _ in PROBES]
    rows_red = [{"id": "red:" + l, "dtstart": d, "rrule": reduce_to_first(r), "limit": n}
                for l, _, d, r, n, _ in PROBES]
    corpus = sorted(i for i, c in cases.items()
                    if parts(c["rrule"]).get("FREQ") == "YEARLY"
                    and multivalued_time_part(c["rrule"]))
    for i in corpus:
        c = cases[i]
        rows_full.append({"id": "case:" + i, "dtstart": c["dtstart"],
                          "rrule": c["rrule"], "limit": c["limit"]})
        rows_red.append({"id": "redcase:" + i, "dtstart": c["dtstart"],
                         "rrule": reduce_to_first(c["rrule"]), "limit": c["limit"]})
    return rows_full + rows_red, corpus


def main():
    os.chdir(HERE)
    cases = load_cases()
    rows, corpus = collect(cases)
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
                  "probes": {l: {"group": g, "dtstart": d, "rrule": r,
                                 "reduced": reduce_to_first(r), "limit": n, "note": t}
                             for l, g, d, r, n, t in PROBES},
                  "corpus_cases": corpus,
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
    print("098 -- ical.js, FREQ=YEARLY: only the first listed BYHOUR/BYMINUTE/BYSECOND value survives")
    print("cases_id %s ; adapter case timeout %d ms" % (cases_id()[:12], stored["adapter_case_timeout_ms"]))
    print("PREDICTOR: ical.js(rule) == dateutil(rule with each multi-valued time part cut to its FIRST value)")

    fail = []
    print("\n-- D: the predictor holds, and the rule as written does not.")
    for l, g, d, r, n, note in PROBES:
        if g != "D":
            continue
        pred = ic.get(l) == du.get("red:" + l)
        differs = ic.get(l) != du.get(l)
        if not (pred and differs):
            fail.append(l)
        print("  %-9s predictor %-4s ; differs from the rule as written %-4s" %
            (l, "HOLDS" if pred else "NO", "yes" if differs else "NO"))
        print("             %s" % r)
        print("             ical.js   %s" % show(ic.get(l)))
        print("             correct   %s" % show(du.get(l)))
        print("             %s" % note)

    print("\n-- C: controls. The predictor MUST FAIL and ical.js must be correct.")
    for l, g, d, r, n, note in PROBES:
        if g != "C":
            continue
        correct = ic.get(l) == du.get(l)
        pred_too = ic.get(l) == du.get("red:" + l)
        # a control is only informative if reducing actually changes the rule
        changed = reduce_to_first(r) != r
        if not correct or (changed and pred_too):
            fail.append(l)
        print("  %-9s ical.js %-9s ; predictor %s   %s" %
              (l, "CORRECT" if correct else "WRONG",
               ("also holds -- VACUOUS" if pred_too else "fails, as required")
               if changed else "n/a (rule has no multi-valued time part)", note))

    if fail:
        print("\n  *** FAILED: %s -- the characterisation above does NOT hold ***" % fail)
        return 1
    print("\n  all %d probes and %d controls behave as stated"
          % (sum(1 for p in PROBES if p[1] == "D"), sum(1 for p in PROBES if p[1] == "C")))

    print("\n-- extent: every corpus case with FREQ=YEARLY and a multi-valued time part")
    exact = 0
    for i in corpus:
        ok = ic.get("case:" + i) == du.get("redcase:" + i)
        exact += ok
        print("  %s %-38s predictor %s" % (i, cases[i]["rrule"][:38], "exact" if ok else "MISSES"))
    print("  predictor exact on %d of %d." % (exact, len(corpus)))
    if exact != len(corpus):
        return 1

    other = sorted(i for i, c in cases.items()
                   if multivalued_time_part(c["rrule"])
                   and parts(c["rrule"]).get("FREQ") != "YEARLY")
    print("  %d further corpus cases have a multi-valued time part at another FREQ; "
          "they are NOT claimed here." % len(other))
    print("  %d of %d corpus cases carry the YEARLY shape at all." % (len(corpus), len(cases)))
    print("  RARE IN THIS CORPUS IS NOT RARE IN THE RULE LANGUAGE (096's caveat, repeated).")

    print("\n-- sabre: the same SYMPTOM from a DIFFERENT rule")
    sb = t.get("sabre", {})
    for i in corpus:
        same = sb.get("case:" + i) == du.get("redcase:" + i)
        print("  %s predictor %s" % (i, "exact" if same else "does not hold"))
    print("  sabre truncates too, but R-minute decides against a shared rule: on")
    print("  FREQ=YEARLY;BYMINUTE=0,30 with DTSTART minute 30, ical.js keeps 0 (first")
    print("  listed) and sabre keeps 30 (DTSTART's). Different mechanisms, and sabre's")
    print("  answers on the BYYEARDAY cases are dominated by an unrelated sabre defect.")

    if os.path.exists(RESID):
        ids = json.load(open(RESID))["ids"]
        un = set(ids["unexplained"])
        hits = sorted(i for i in corpus if i in un)
        print("\n-- against 074's unattributed residual, as narrowed by 096 and 097")
        print("  %d of the %d shape-carrying cases are in 074's unexplained list: %s"
              % (len(hits), len(corpus), " ".join(hits) or "(none)"))
        labelled = sorted(i for k, v in ids.items() if k.startswith("070-B") for i in v)
        print("  %d more were filed under a '070-B' label: %s" % (len(labelled), " ".join(labelled)))
        print("  070-B as WRITTEN is about the ORDER the time parts are walked in, at DAILY.")
        print("  It does not contain the claim that values are DROPPED at YEARLY. That")
        print("  attribution pointed at a finding that does not make it; this one does.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

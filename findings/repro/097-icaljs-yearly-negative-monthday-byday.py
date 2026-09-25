#!/usr/bin/env python3
"""097 -- ical.js: a negative BYMONTHDAY contributes nothing at FREQ=YEARLY when
BYDAY is present, and two spec-boundary results found on the way.

Default mode is READ-ONLY and ADAPTER-FREE: it replays the adapter answers
stored in findings/data/097-*.json and re-derives the corpus extent from
conformance/cases.ndjson. It stamps the repository's own cases_id and REFUSES
if the corpus has moved (rule 94: an answer is only meaningful at the depth and
corpus it was asked for).

  python3 findings/repro/097-icaljs-yearly-negative-monthday-byday.py
  python3 findings/repro/097-icaljs-yearly-negative-monthday-byday.py --run-adapters
      # needs node, java, php; WRITES findings/data/097-*.json

WHAT THIS ESTABLISHES
  D  the defect: FREQ=YEARLY + a negative BYMONTHDAY + BYDAY -> ical.js empty
  N  the NEGATIVE result: this is NOT ical4j's 051 defect B. ical.js handles an
     ordinal BYDAY in its limiting role correctly.
  S  two spec-boundary results, in OPPOSITE directions, in the same library.

The adapter timeout matters here. At the adapter's default 2000 ms two of these
probes report `timeout`; they are SLOW, not non-terminating -- at 45000 ms every
one of them answers. This script sets RRULE_CASE_TIMEOUT_MS itself so the
distinction cannot be lost by accident.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(HERE, "findings", "data", "097-icaljs-yearly-negative-monthday-byday.json")
RESID = os.path.join(HERE, "findings", "data", "074-icaljs-residual-reproduced.json")
TIMEOUT_MS = "45000"

ADAPTERS = [
    ("dateutil",  ["python3", "conformance/adapters/dateutil_adapter.py"]),
    ("icaljs",    ["node", "conformance/adapters/icaljs_adapter.js"]),
    ("rrulejs",   ["node", "conformance/adapters/rrulejs_adapter.js"]),
    ("sabre",     ["php", "conformance/adapters/php/vobject_adapter.php"]),
    ("dmfs",      ["java", "-cp", "conformance/adapters/java/classes:conformance/adapters/java/libs/*", "DmfsAdapter"]),
    ("ical4j411", ["java", "-cp", "conformance/adapters/java/classes:conformance/adapters/java/libs/*", "Ical4jAdapter"]),
    ("ical4j430", ["java", "-cp", "conformance/adapters/java/classes:conformance/adapters/java/libs430/*:conformance/adapters/java/libs/*", "Ical4jAdapter"]),
]

# (label, group, dtstart, rrule, limit, what it establishes)
#   group D = the defect (criterion: ical.js EMPTY, the field is not)
#         C = a control ical.js must pass, criterion EQUALS dateutil
#         N = a control whose criterion is only NON-EMPTY, stated separately because
#             ical.js is known to differ from dateutil here for a DIFFERENT reason
#         S = a spec boundary
PROBES = [
    ("R1",       "D", "20240429T090000", "FREQ=YEARLY;BYMONTHDAY=-2;BYDAY=MO", 6,
     "corpus case 9346b18d8869's shape: ical.js empty, dateutil and rrule.js answer"),
    ("R2",       "D", "20331230T090000", "FREQ=YEARLY;BYMONTHDAY=15,-2;BYDAY=-1FR", 6,
     "corpus case 88a59d144b92: the answer comes only from -2, so dropping it empties it"),
    ("D-2days",  "D", "20240429T090000", "FREQ=YEARLY;BYMONTHDAY=-2;BYDAY=MO,TU", 6,
     "two plain weekdays, still empty: not about which weekday"),
    ("D-neg1",   "D", "20240429T090000", "FREQ=YEARLY;BYMONTHDAY=-1;BYDAY=MO", 6,
     "-1 as well as -2"),
    ("D-bymonth","D", "20240429T090000", "FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=-2;BYDAY=MO", 4,
     "an explicit BYMONTH does not rescue it"),
    ("D-int2",   "D", "20240429T090000", "FREQ=YEARLY;INTERVAL=2;BYMONTHDAY=-2;BYDAY=MO", 4,
     "INTERVAL is irrelevant"),
    ("D-byhour", "D", "20240429T090000", "FREQ=YEARLY;BYMONTHDAY=-2;BYHOUR=9;BYDAY=MO", 4,
     "an added BYHOUR is irrelevant"),
    ("D-all7",   "D", "20240429T090000", "FREQ=YEARLY;BYMONTHDAY=-2;BYDAY=MO,TU,WE,TH,FR,SA,SU", 4,
     "BYDAY that excludes NOTHING is still empty: the candidate set is empty, the filter is not the cause"),
    # --- controls. ical.js must pass these or the characterisation is wrong. ---
    ("C-pos",    "C", "20240429T090000", "FREQ=YEARLY;BYMONTHDAY=2;BYDAY=MO", 6,
     "control: POSITIVE monthday, same shape -- ical.js agrees with dateutil"),
    ("C-monthly","C", "20240429T090000", "FREQ=MONTHLY;BYMONTHDAY=-2;BYDAY=MO", 6,
     "control: same by-parts at MONTHLY -- all seven agree. FREQ=YEARLY is load-bearing"),
    ("C-yearday","C", "20240429T090000", "FREQ=YEARLY;BYYEARDAY=-2;BYDAY=MO", 4,
     "control: a NEGATIVE BYYEARDAY limited by BYDAY is correct. Not about negatives in general"),
    ("C-noday",  "N", "20240429T090000", "FREQ=YEARLY;BYMONTH=4,12;BYMONTHDAY=-2", 4,
     "control: negative monthday at YEARLY WITHOUT BYDAY is NON-EMPTY. BYDAY is load-bearing. "
     "It is NOT equal to dateutil, and the one element that differs is 096's defect J"),
    ("C-ordinal","C", "20270301T090000", "FREQ=MONTHLY;BYMONTHDAY=1;BYDAY=1MO", 4,
     "THE NEGATIVE RESULT: 051 B's own minimal case. ical.js is CORRECT; ical4j is empty"),
    ("C-ord-yr", "C", "20240429T090000", "FREQ=YEARLY;BYMONTHDAY=2;BYDAY=2MO", 4,
     "control: ordinal BYDAY limiting at YEARLY too"),
    # --- spec boundaries, both directions ---
    ("S-weekly", "S", "20240429T090000", "FREQ=WEEKLY;BYMONTHDAY=-2", 4,
     "RFC 5545 3.3.10: BYMONTHDAY MUST NOT appear with FREQ=WEEKLY. Who rejects it?"),
    ("S-wkpos",  "S", "20240429T090000", "FREQ=WEEKLY;BYMONTHDAY=2", 4,
     "same, positive: the rejection is about the by-part, not the sign"),
    ("S-wkno",   "S", "20240429T090000", "FREQ=YEARLY;BYWEEKNO=18;BYMONTHDAY=29", 4,
     "BYWEEKNO with BYMONTHDAY at YEARLY is NOT forbidden by 3.3.10. Who rejects it anyway?"),
]

LINEAGE_NOTE = ("sabre is excluded from unanimity counts for its known unconditional "
                "DTSTART (finding 024); rrule.js and dateutil are ONE vote (rule 24).")


def run(cmd, rows):
    env = dict(os.environ, RRULE_CASE_TIMEOUT_MS=TIMEOUT_MS)
    inp = "\n".join(json.dumps(r) for r in rows)
    p = subprocess.run(cmd, input=inp, capture_output=True, text=True, cwd=HERE, env=env)
    out = {}
    for line in p.stdout.splitlines():
        if not line.startswith("{"):
            continue
        o = json.loads(line)
        if "error" in o:
            out[o["id"]] = {"error": o["error"]}
        else:
            out[o["id"]] = {"occurrences": o.get("occurrences")}
    return out


def cases_id():
    """The repository's OWN cases_id. Never re-hash cases.ndjson (096's near-miss)."""
    sys.path.insert(0, os.path.join(HERE, "tools"))
    import corpus_id
    return corpus_id.compute()["cases_id"]


def load_cases():
    return {c["id"]: c for c in
            (json.loads(l) for l in open(os.path.join(HERE, "conformance", "cases.ndjson")))}


def negative_monthday_shape(rrule):
    """The defect's rule shape, derived from the rule text alone."""
    p = {}
    for part in rrule.split(";"):
        k, _, v = part.partition("=")
        p[k] = v
    if p.get("FREQ") != "YEARLY" or "BYDAY" not in p or "BYMONTHDAY" not in p:
        return None
    vals = [int(x) for x in p["BYMONTHDAY"].split(",")]
    if not any(v < 0 for v in vals):
        return None
    return "all-negative" if all(v < 0 for v in vals) else "mixed-sign"


def show(v):
    if v is None:
        return "no answer line"
    if "error" in v:
        return "REJECTED: " + v["error"]
    o = v["occurrences"]
    return "(empty)" if o == [] else " ".join(x[:8] for x in o)


def main():
    os.chdir(HERE)
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
                  "probes": {l: {"group": g, "dtstart": d, "rrule": r, "limit": n, "note": t}
                             for l, g, d, r, n, t in PROBES},
                  "adapters": table}
        json.dump(stored, open(DATA, "w"), indent=1, sort_keys=True)
        print("-> %s" % DATA)

    if not stored:
        sys.exit("no stored answers; run once with --run-adapters")
    if stored.get("cases_id") != cases_id():
        sys.exit("REFUSING: stored answers were taken at cases_id %s, corpus is now %s. "
                 "Re-run with --run-adapters." % (str(stored.get("cases_id"))[:12], cases_id()[:12]))

    table = stored["adapters"]
    print("097 -- ical.js, FREQ=YEARLY with a negative BYMONTHDAY under BYDAY")
    print("cases_id %s ; adapter case timeout %d ms" % (cases_id()[:12], stored["adapter_case_timeout_ms"]))
    print(LINEAGE_NOTE)

    field = [n for n, _ in ADAPTERS if n not in ("icaljs", "sabre", "rrulejs")]

    print("\n-- D: the defect. ical.js empty, the rest answer.")
    empt = 0
    for l, g, d, r, n, t in PROBES:
        if g != "D":
            continue
        ic = table["icaljs"].get(l)
        is_empty = ic is not None and ic.get("occurrences") == []
        empt += is_empty
        others_nonempty = sum(1 for f in field
                              if table.get(f, {}).get(l, {}).get("occurrences"))
        print("  %-9s ical.js %-9s ; %d/%d of %s answer non-empty" %
              (l, "EMPTY" if is_empty else "not empty", others_nonempty, len(field),
               "/".join(field)))
        print("             %s" % t)
    print("  ical.js returns the EMPTY LIST on %d of %d defect probes" % (empt, 8))

    print("\n-- C: controls ical.js must pass, criterion EQUALS dateutil.")
    print("   A characterisation that fails these is wrong, so they are checked, not narrated.")
    bad = []
    for l, g, d, r, n, t in PROBES:
        if g != "C":
            continue
        ok = table["icaljs"].get(l) == table["dateutil"].get(l)
        if not ok:
            bad.append(l)
        print("  %-9s ical.js %s dateutil   %s" % (l, "==" if ok else "!=", t))
    print("\n-- N: control whose criterion is NON-EMPTY only, not equality.")
    for l, g, d, r, n, t in PROBES:
        if g != "N":
            continue
        ic = table["icaljs"].get(l)
        ok = bool(ic and ic.get("occurrences"))
        if not ok:
            bad.append(l)
        print("  %-9s ical.js %s   %s" % (l, "NON-EMPTY" if ok else "EMPTY -- FAILS", t))
        print("             ical.js  %s" % show(ic))
        print("             dateutil %s" % show(table["dateutil"].get(l)))
    if bad:
        print("\n  *** CONTROLS FAILED: %s -- the characterisation above does NOT hold ***" % bad)
        return 1
    print("\n  all %d controls pass"
          % sum(1 for p in PROBES if p[1] in ("C", "N")))

    print("\n-- S: the spec boundary, both directions.")
    for l, g, d, r, n, t in PROBES:
        if g != "S":
            continue
        print("  %s  %s" % (l, r))
        print("    %s" % t)
        for name, _ in ADAPTERS:
            print("      %-10s %s" % (name, show(table.get(name, {}).get(l))))

    print("\n-- extent in this corpus (derived from cases.ndjson, no adapter)")
    cases = load_cases()
    found = {}
    for c in cases.values():
        s = negative_monthday_shape(c["rrule"])
        if s:
            found.setdefault(s, []).append(c["id"])
    tot = 0
    for k in sorted(found):
        print("  %-13s %d  %s" % (k, len(found[k]), " ".join(sorted(found[k]))))
        tot += len(found[k])
    print("  %d of %d corpus cases carry the shape at all." % (tot, len(cases)))
    print("  RARE IN THIS CORPUS IS NOT RARE IN THE RULE LANGUAGE (096's caveat, repeated).")

    if os.path.exists(RESID):
        un = set(json.load(open(RESID))["ids"]["unexplained"])
        hits = sorted(i for v in found.values() for i in v if i in un)
        print("\n-- against 074's unattributed residual, as narrowed by 096")
        print("  %d of the shape-carrying cases are in 074's unexplained list: %s"
              % (len(hits), " ".join(hits)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""099 -- ical.js, FREQ=YEARLY with BYMONTHDAY and no other expanding by-part.

Two separable results from one code branch, and they must not be conflated:

  N  A DEFECT THAT IS ical.js's ALONE. The anchor year is read off `this.last`
     AFTER setup_defaults() has assigned the RAW first listed BYMONTHDAY value
     to `.day`. A negative first value normalises backwards into the previous
     month -- and when the anchor month is JANUARY, into the previous YEAR.
     The whole year lattice is then anchored at (DTSTART year - 1), so with
     INTERVAL > 1 every occurrence is late by INTERVAL - 1 years.

  M  A DISPUTE, NOT A DEFECT. On the same branch ical.js confines the expansion
     to DTSTART's month instead of all twelve. Four of six implementations do
     the same. RFC 5545 3.3.10's table says BYMONTHDAY EXPANDS at YEARLY, and
     dateutil and rrule.js follow it; sabre, dmfs, ical4j and ical.js do not.
     This script reports the split and does NOT call it a defect (rule 24:
     dateutil and rrule.js are ONE vote).

Keeping these apart is the whole point. M makes most of the in-scope corpus
cases disagree with the reference, so a naive count would attribute to ical.js
a behaviour most of the field shares. N is what ical.js does that nobody else
does, and the July control below is what separates them.

Default mode is READ-ONLY and ADAPTER-FREE: it replays the adapter answers
stored in findings/data/099-*.json and re-derives the corpus extent from
conformance/cases.ndjson. It stamps the repository's own cases_id and REFUSES
if the corpus has moved (rule 94).

  python3 findings/repro/099-icaljs-yearly-monthday-anchor.py
  python3 findings/repro/099-icaljs-yearly-monthday-anchor.py --run-adapters
      # needs node, java, php; WRITES findings/data/099-*.json
"""
import calendar, datetime, json, os, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(HERE, "findings", "data", "099-icaljs-yearly-monthday-anchor.json")
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
#   N = the anchor defect: ical.js's first year is DTSTART year + INTERVAL - 1
#   C = a control the characterisation must pass
#   M = the month-expansion dispute; reported as a split, never scored as a defect
PROBES = [
    ("N-int2",    "N", "20260130T090000", "FREQ=YEARLY;INTERVAL=2;BYMONTHDAY=-2", 6,
     "corpus case 7a381d6a4176's shape: first year 2027, not 2026"),
    ("N-int3",    "N", "20260130T090000", "FREQ=YEARLY;INTERVAL=3;BYMONTHDAY=-2", 6,
     "INTERVAL=3 -> first year 2028. The lag is INTERVAL-1, so it grows with INTERVAL"),
    ("N-int4",    "N", "20260127T090000", "FREQ=YEARLY;INTERVAL=4;BYMONTHDAY=-5;WKST=SU;BYSETPOS=1", 6,
     "corpus case 57bd6869b586: INTERVAL=4 -> first year 2029, lag 3"),
    ("N-int5",    "N", "20260130T090000", "FREQ=YEARLY;INTERVAL=5;BYMONTHDAY=-2", 4,
     "INTERVAL=5 -> lag 4. The anchor is fixed at 2025; only the stride changes"),
    ("N-md31",    "N", "20260130T090000", "FREQ=YEARLY;INTERVAL=3;BYMONTHDAY=-31", 4,
     "magnitude is irrelevant: -31 borrows into 2025 just as -2 does"),
    ("N-first",   "N", "20260130T090000", "FREQ=YEARLY;INTERVAL=3;BYMONTHDAY=-2,15", 4,
     "FIRST LISTED value decides: -2 first -> shifted"),
    # --- controls. The characterisation is wrong if any of these fails. ---
    ("C-order",   "C", "20260130T090000", "FREQ=YEARLY;INTERVAL=3;BYMONTHDAY=15,-2", 4,
     "SAME SET, positive first -> NOT shifted. Only setup_defaults' [0] is read"),
    ("C-pos",     "C", "20260130T090000", "FREQ=YEARLY;INTERVAL=3;BYMONTHDAY=30", 4,
     "positive monthday, same shape -> first year 2026. The sign is load-bearing"),
    ("C-july",    "C", "20260730T090000", "FREQ=YEARLY;INTERVAL=3;BYMONTHDAY=-2", 4,
     "THE CONTROL THAT SEPARATES N FROM M: July DTSTART, -2 borrows to June and "
     "stays in 2026 -> no shift, and ical.js then equals sabre/dmfs/ical4j exactly"),
    ("C-feb",     "C", "20260220T090000", "FREQ=YEARLY;INTERVAL=3;BYMONTHDAY=-2", 4,
     "February DTSTART: borrows to January, same year -> no shift. JANUARY is load-bearing"),
    ("C-dec",     "C", "20261220T090000", "FREQ=YEARLY;INTERVAL=3;BYMONTHDAY=-2", 4,
     "December DTSTART: no shift"),
    ("C-bymonth", "C", "20260130T090000", "FREQ=YEARLY;INTERVAL=3;BYMONTH=7;BYMONTHDAY=-2", 4,
     "an explicit BYMONTH moves the anchor month off January -> no shift"),
    ("C-monthly", "C", "20260131T090000", "FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=-1", 6,
     "same parts at MONTHLY are CORRECT. FREQ=YEARLY is load-bearing"),
    ("C-yearday", "C", "20260130T090000", "FREQ=YEARLY;INTERVAL=3;BYYEARDAY=-2", 4,
     "a negative BYYEARDAY is correct: not about negatives in general"),
    ("C-byday",   "C", "20260130T090000", "FREQ=YEARLY;INTERVAL=3;BYDAY=-1MO", 4,
     "a negative ordinal BYDAY is correct: not about negatives in general"),
    # --- the dispute, reported as a split ---
    ("M-neg",     "M", "20260130T090000", "FREQ=YEARLY;INTERVAL=2;BYMONTHDAY=-2", 6,
     "does BYMONTHDAY expand over all twelve months at YEARLY?"),
    ("M-pos",     "M", "20260130T090000", "FREQ=YEARLY;BYMONTHDAY=30", 6,
     "the same question with a POSITIVE value, where N is not in play at all"),
]

LINEAGE_NOTE = ("sabre is excluded from unanimity counts for its known unconditional "
                "DTSTART (finding 024); rrule.js and dateutil are ONE vote (rule 24).")


def dim(y, m):
    return calendar.monthrange(y, m)[1]


def parse_rrule(r):
    p = {}
    for kv in r.split(";"):
        k, _, v = kv.partition("=")
        p[k] = v
    return p


def predict(dtstart, parts, limit):
    """A model of the partCount==1 BYMONTHDAY branch of expand_year_days(),
    written from the source and then tested against the adapter.

    It knows nothing about BYSETPOS -- and matching anyway is itself a result:
    BYSETPOS is not among the five parts expand_year_days() counts, so it never
    reaches this path."""
    L = [int(x) for x in parts["BYMONTHDAY"].split(",")]
    iv = int(parts.get("INTERVAL", 1))
    m0 = dtstart.month
    # setup_defaults() assigns the RAW L[0] to this.last.day; Time normalises it.
    anchor = datetime.date(dtstart.year, m0, 1) + datetime.timedelta(days=L[0] - 1)
    year, out, guard = anchor.year, [], 0
    while len(out) < limit and guard < 4000:
        guard += 1
        days = []
        for md in L:
            v = md + dim(year, m0) + 1 if md < 0 else md
            days.append(datetime.date(year, m0, 1) + datetime.timedelta(days=v - 1))
        for d in sorted(set(days)):
            t = datetime.datetime(d.year, d.month, d.day,
                                  dtstart.hour, dtstart.minute, dtstart.second)
            if t >= dtstart and len(out) < limit:
                out.append(t)
        year += iv
    return [d.strftime("%Y%m%dT%H%M%S") for d in out]


def in_scope(rrule):
    p = parse_rrule(rrule)
    if p.get("FREQ") != "YEARLY" or "BYMONTHDAY" not in p:
        return None
    if any(k in p for k in ("BYMONTH", "BYDAY", "BYYEARDAY", "BYWEEKNO")):
        return None
    return p


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
    return [json.loads(l) for l in open(os.path.join(HERE, "conformance", "cases.ndjson"))]


def show(v):
    if v is None:
        return "no answer line"
    if "error" in v:
        return "REJECTED: " + v["error"]
    o = v["occurrences"]
    return "(empty)" if o == [] else " ".join(x[:8] for x in o)


def first_year(v):
    if not v or "error" in v or not v["occurrences"]:
        return None
    return int(v["occurrences"][0][:4])


def main():
    os.chdir(HERE)
    cases = load_cases()
    scope = [(c, in_scope(c["rrule"])) for c in cases]
    scope = [(c, p) for c, p in scope if p]

    corpus_rows = [{"id": c["id"], "dtstart": c["dtstart"], "rrule": c["rrule"],
                    "limit": c["limit"]} for c, _ in scope]
    probe_rows = [{"id": l, "dtstart": d, "rrule": r, "limit": n}
                  for l, _, d, r, n, _ in PROBES]

    stored = json.load(open(DATA)) if os.path.exists(DATA) else {}
    if "--run-adapters" in sys.argv:
        table = {}
        for name, cmd in ADAPTERS:
            got = run(cmd, probe_rows)
            if got:
                table[name] = got
            else:
                print("  (%s produced nothing, skipped)" % name)
        stored = {"cases_id": cases_id(),
                  "adapter_case_timeout_ms": int(TIMEOUT_MS),
                  "probes": {l: {"group": g, "dtstart": d, "rrule": r, "limit": n, "note": t}
                             for l, g, d, r, n, t in PROBES},
                  "adapters": table,
                  "corpus_icaljs": run(dict(ADAPTERS)["icaljs"], corpus_rows)}
        json.dump(stored, open(DATA, "w"), indent=1, sort_keys=True)
        print("-> %s" % DATA)

    if not stored:
        sys.exit("no stored answers; run once with --run-adapters")
    if stored.get("cases_id") != cases_id():
        sys.exit("REFUSING: stored answers were taken at cases_id %s, corpus is now %s. "
                 "Re-run with --run-adapters." % (str(stored.get("cases_id"))[:12], cases_id()[:12]))

    table = stored["adapters"]
    print("099 -- ical.js, FREQ=YEARLY with BYMONTHDAY and no other expanding by-part")
    print("cases_id %s ; adapter case timeout %d ms" % (cases_id()[:12], stored["adapter_case_timeout_ms"]))
    print(LINEAGE_NOTE)

    field = [n for n, _ in ADAPTERS if n not in ("icaljs", "sabre", "rrulejs")]
    bad = []

    print("\n-- N: the anchor defect. Expected first year = DTSTART year + INTERVAL - 1.")
    for l, g, d, r, n, t in PROBES:
        if g != "N":
            continue
        iv = int(parse_rrule(r).get("INTERVAL", 1))
        want = int(d[:4]) + iv - 1
        got = first_year(table["icaljs"].get(l))
        ok = got == want
        if not ok:
            bad.append(l)
        others = sorted({first_year(table.get(f, {}).get(l)) for f in field} - {None})
        print("  %-9s ical.js first year %s (predicted %d) %s ; %s first year %s"
              % (l, got, want, "OK" if ok else "*** MISMATCH ***",
                 "/".join(field), others))
        print("             %s" % t)

    print("\n-- C: controls. ical.js must NOT be shifted on any of these.")
    for l, g, d, r, n, t in PROBES:
        if g != "C":
            continue
        want = int(d[:4])
        got = first_year(table["icaljs"].get(l))
        # a first occurrence may legitimately fall in a later year when DTSTART
        # itself is past the in-year candidate; the criterion is "not later than
        # the un-shifted lattice would allow", i.e. equal to DTSTART's year here.
        ok = got == want
        if not ok:
            bad.append(l)
        print("  %-9s ical.js first year %s, DTSTART year %d  %s"
              % (l, got, want, "OK" if ok else "*** SHIFTED -- characterisation is wrong ***"))
        print("             %s" % t)

    if bad:
        print("\n  *** FAILED: %s -- the characterisation above does NOT hold ***" % bad)
        return 1
    print("\n  all %d N probes and %d controls behave as characterised"
          % (sum(1 for p in PROBES if p[1] == "N"), sum(1 for p in PROBES if p[1] == "C")))

    print("\n-- M: the month-expansion DISPUTE. Not scored as a defect.")
    for l, g, d, r, n, t in PROBES:
        if g != "M":
            continue
        print("  %s  %s   (%s)" % (l, r, t))
        months = {}
        for name, _ in ADAPTERS:
            v = table.get(name, {}).get(l)
            k = "all twelve" if v and not v.get("error") and len({x[4:6] for x in v["occurrences"]}) > 1 \
                else "DTSTART's month only"
            months.setdefault(k, []).append(name)
            print("      %-10s %s" % (name, show(v)))
        for k in sorted(months):
            print("    %-22s %s" % (k, " ".join(months[k])))
    print("  RFC 5545 3.3.10 lists BYMONTHDAY as EXPAND at FREQ=YEARLY. The field is split,")
    print("  so this finding records the split and does not call either side a defect.")

    print("\n-- the predictor, against ical.js's answers on every in-scope corpus case")
    stored_corpus = stored.get("corpus_icaljs", {})
    exact = miss = 0
    misses = []
    for c, p in scope:
        act = stored_corpus.get(c["id"], {}).get("occurrences")
        if act is None:
            continue
        ds = datetime.datetime.strptime(c["dtstart"], "%Y%m%dT%H%M%S")
        if predict(ds, p, c["limit"]) == act:
            exact += 1
        else:
            miss += 1
            misses.append(c["id"])
    print("  in-scope corpus cases: %d of %d" % (len(scope), len(cases)))
    print("  predictor reproduces ical.js EXACTLY on %d, misses %d: %s"
          % (exact, miss, " ".join(misses) or "-"))
    print("  The misses are NOT claimed. Both have DTSTART in February with a BYMONTHDAY")
    print("  whose magnitude exceeds February's length, where by_data.BYMONTHDAY is")
    print("  additionally rewritten by normalizeByMonthDayRules between years.")

    if os.path.exists(RESID):
        un = set(json.load(open(RESID))["ids"]["unexplained"])
        hits = sorted(c["id"] for c, _ in scope if c["id"] in un)
        got = [i for i in hits if i not in misses]
        print("\n-- against 074's unattributed residual")
        print("  in scope and unattributed: %d  %s" % (len(hits), " ".join(hits)))
        print("  reproduced exactly here  : %d  %s" % (len(got), " ".join(got)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

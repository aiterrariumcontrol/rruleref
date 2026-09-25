#!/usr/bin/env python3
"""100 -- ical.js, FREQ=MONTHLY with BOTH BYMONTHDAY and BYDAY.

ONE root cause, TWO symptoms, and the second one is a thrown error.

ROOT. recur_iterator.js init() reaches the MONTHLY/BYDAY block (line ~305) with
`this.last` ALREADY carrying the raw first listed BYMONTHDAY value in `.day`,
assigned by setup_defaults() and then normalised by Time. A NEGATIVE first value
therefore drags `this.last` back into an EARLIER MONTH -- one month for small
magnitudes, two when |value| exceeds the length of DTSTART's month. The block
then treats that earlier month as the starting month.

  S1  A THROWN ERROR on a valid rule. `daysInMonth` is captured ONCE, from the
      wrongly-anchored month, before the BYDAY loop. _byDayAndMonthDay(true) may
      then land in a LONGER month, and the guard

          if (this.last.day > daysInMonth || this.last.day == 0)
              throw new Error("Malformed values in BYDAY part");

      compares a day from one month against another month's length. The message
      names BYDAY, but BYDAY's VALUE is not what decides it -- the lengths of two
      months are. FREQ=MONTHLY;BYMONTHDAY=-1;BYDAY=SU is rejected outright for
      DTSTART in March, May, July, August, October and December, and accepted for
      the other six, which is a calendar fact about the PRECEDING month.

  S2  When it does not throw, the month lattice is on the WRONG INTERVAL PHASE.
      Every occurrence sits at a month offset congruent to -shift (mod INTERVAL)
      instead of 0, so with INTERVAL > 1 every occurrence is wrong and DTSTART
      itself is dropped. INTERVAL=1 hides S2 completely -- but NOT S1.

This is the same setup_defaults() [0] raw return as findings 098 and 099, now on
a third branch. 099's C-monthly control -- MONTHLY with BYMONTHDAY and NO BYDAY
is correct -- STANDS EXACTLY AS WRITTEN and is reproduced here as C-nobyday. It
was my own operating note, not 099, that over-read that control into "the anchor
mechanism cannot explain the MONTHLY residuals". BYDAY is the difference.

Default mode is READ-ONLY and ADAPTER-FREE: it replays the adapter answers stored
in findings/data/100-*.json and re-derives the corpus extent from
conformance/cases.ndjson. It stamps the repository's own cases_id and REFUSES if
the corpus has moved (rule 94).

  python3 findings/repro/100-icaljs-monthly-monthday-anchor.py
  python3 findings/repro/100-icaljs-monthly-monthday-anchor.py --run-adapters
      # needs node, java, php; WRITES findings/data/100-*.json
"""
import calendar, datetime, json, os, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(HERE, "findings", "data", "100-icaljs-monthly-monthday-anchor.json")
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
#   S1 = the thrown error   S2 = the wrong INTERVAL phase   C = a control
PROBES = [
    ("S1-mar",     "S1", "20260315T090000", "FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=-1;BYDAY=SU", 3,
     "March DTSTART: anchored into 28-day February, lands on a 31-day month -> REJECTED"),
    ("S1-int1",    "S1", "20260315T090000", "FREQ=MONTHLY;BYMONTHDAY=-1;BYDAY=SU", 3,
     "INTERVAL=1 does NOT hide S1: still REJECTED. S1 reaches the commonest rule shape"),
    ("S1-md5",     "S1", "20260315T090000", "FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=-5;BYDAY=SU", 3,
     "-5 also anchors into February, but lands on a day <= 28 -> accepted, and WRONG PHASE"),
    ("S1-two",     "S1", "20260315T090000", "FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=-1,5;BYDAY=SU", 3,
     "a second, positive value does not help: only the FIRST listed value is read -> REJECTED"),
    ("S2-jan",     "S2", "20260131T090000", "FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=-1;BYDAY=SA", 4,
     "corpus case e1b4925a5263's shape. Accepted, and every month offset is 2 mod 3"),
    ("S2-int2",    "S2", "20260131T090000", "FREQ=MONTHLY;INTERVAL=2;BYMONTHDAY=-1;BYDAY=SA", 4,
     "INTERVAL=2: offsets 1 mod 2, and DTSTART 2026-01-31 -- itself a valid match -- is DROPPED"),
    ("S2-md31",    "S2", "20260315T090000", "FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=-31;BYDAY=SU", 4,
     "|value| > March's length borrows TWO months back to January -> offsets 1 mod 3, not 2"),
    # --- controls. The characterisation is wrong if any of these fails. ---
    ("C-pos",      "C", "20260131T090000", "FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=31;BYDAY=SA", 4,
     "SAME MEANING for January, positive spelling -> correct phase. The SIGN is load-bearing"),
    ("C-order",    "C", "20260131T090000", "FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=15,-1;BYDAY=SA", 4,
     "SAME SET as S2-jan's superset, positive FIRST -> correct. Only setup_defaults' [0] is read"),
    ("C-nobyday",  "C", "20260131T090000", "FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=-1", 4,
     "099's C-monthly, reproduced: WITHOUT BYDAY the same parts are CORRECT. BYDAY is the difference"),
    ("C-nomonthday", "C", "20260131T090000", "FREQ=MONTHLY;INTERVAL=3;BYDAY=-1SA", 4,
     "WITHOUT BYMONTHDAY a negative ordinal BYDAY is correct: not about negatives in general"),
    ("C-int1pos",  "C", "20260315T090000", "FREQ=MONTHLY;BYMONTHDAY=31;BYDAY=SU", 3,
     "S1-int1 with a positive spelling -> accepted. The rejection is not about INTERVAL=1"),
    ("C-jun",      "C", "20260615T090000", "FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=-1;BYDAY=SU", 3,
     "June DTSTART: anchored into 31-day May, so no month is longer -> accepted (wrong phase only)"),
]

# S1's grid: DTSTART month x weekday, one shape. Predicted from the two month
# lengths alone; the prediction is exact or this finding is wrong.
GRID_DOWS = ["SU", "MO", "TU", "WE", "TH", "FR", "SA"]
GRID_YEAR = 2026
GRID_RRULE = "FREQ=MONTHLY;INTERVAL=3;BYMONTHDAY=-1;BYDAY=%s"

LINEAGE_NOTE = ("sabre is excluded from unanimity counts for its known unconditional "
                "DTSTART (finding 024); rrule.js and dateutil are ONE vote (rule 24).")


def dim(y, m):
    return calendar.monthrange(y, m)[1]


def add_months(y, m, k):
    t = (y * 12 + (m - 1)) + k
    return t // 12, t % 12 + 1


def month_offset(y, m, y0, m0):
    return (y * 12 + m) - (y0 * 12 + m0)


def parse_rrule(r):
    p = {}
    for kv in r.split(";"):
        k, _, v = kv.partition("=")
        p[k] = v
    return p


def anchor_month(dtstart, first_md):
    """setup_defaults() assigns the RAW first listed BYMONTHDAY to this.last.day;
    Time normalises it. This is the month init() then treats as the start."""
    d = datetime.date(dtstart.year, dtstart.month, 1) + datetime.timedelta(days=first_md - 1)
    return d.year, d.month


def grid_predict(dtstart_month, dow):
    """For BYMONTHDAY=-1 and ONE plain BYDAY: predict rejection AND first occurrence.

    Anchored in the month before DTSTART's, _byDayAndMonthDay walks the INTERVAL=3
    lattice for the first month whose LAST DAY falls on `dow`; the guard then
    compares that month's length against the ANCHOR month's length."""
    ay, am = anchor_month(datetime.date(GRID_YEAR, dtstart_month, 15), -1)
    want = GRID_DOWS.index(dow)           # 0 = Sunday
    for k in range(0, 400):
        y, m = add_months(ay, am, 3 * k)
        last = datetime.date(y, m, dim(y, m))
        if (last.weekday() + 1) % 7 == want:
            return {"rejected": dim(y, m) > dim(ay, am),
                    "first": "%04d%02d%02d" % (y, m, dim(y, m))}
    return {"rejected": None, "first": None}


def in_scope(rrule):
    """The corpus cases this finding claims: MONTHLY, BOTH parts, first value negative."""
    p = parse_rrule(rrule)
    if p.get("FREQ") != "MONTHLY" or "BYMONTHDAY" not in p or "BYDAY" not in p:
        return None
    if any(k in p for k in ("BYMONTH", "BYYEARDAY", "BYWEEKNO")):
        return None
    if int(p["BYMONTHDAY"].split(",")[0]) >= 0:
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


def show(v, n=4):
    if v is None:
        return "no answer line"
    if "error" in v:
        return "REJECTED: " + v["error"]
    o = v["occurrences"]
    return "(empty)" if o == [] else " ".join(x[:8] for x in o[:n])


def phase_of(v, dtstart, iv):
    """The set of month offsets mod INTERVAL that an answer's occurrences occupy."""
    if not v or "error" in v or not v["occurrences"]:
        return None
    return sorted({month_offset(int(o[:4]), int(o[4:6]), dtstart.year, dtstart.month) % iv
                   for o in v["occurrences"]})


def main():
    os.chdir(HERE)
    cases = load_cases()
    scope = [(c, p) for c, p in ((c, in_scope(c["rrule"])) for c in cases) if p]

    corpus_rows = [{"id": c["id"], "dtstart": c["dtstart"], "rrule": c["rrule"],
                    "limit": c["limit"]} for c, _ in scope]
    probe_rows = [{"id": l, "dtstart": d, "rrule": r, "limit": n}
                  for l, _, d, r, n, _ in PROBES]
    grid_rows = [{"id": "G-%02d-%s" % (m, w), "dtstart": "%04d%02d15T090000" % (GRID_YEAR, m),
                  "rrule": GRID_RRULE % w, "limit": 2}
                 for m in range(1, 13) for w in GRID_DOWS]

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
                  "grid_icaljs": run(dict(ADAPTERS)["icaljs"], grid_rows),
                  "grid_dateutil": run(dict(ADAPTERS)["dateutil"], grid_rows),
                  "corpus_icaljs": run(dict(ADAPTERS)["icaljs"], corpus_rows),
                  "corpus_dateutil": run(dict(ADAPTERS)["dateutil"], corpus_rows)}
        json.dump(stored, open(DATA, "w"), indent=1, sort_keys=True)
        print("-> %s" % DATA)

    if not stored:
        print("no stored data; run with --run-adapters first")
        return 1

    here_id = cases_id()
    if stored.get("cases_id") != here_id:
        print("REFUSING: data was taken at cases %s, corpus is now %s (rule 94)"
              % (stored.get("cases_id"), here_id))
        return 1

    print("100 -- ical.js, FREQ=MONTHLY with BOTH BYMONTHDAY and BYDAY")
    print("corpus %s   adapter timeout %s ms" % (here_id, stored["adapter_case_timeout_ms"]))
    print(LINEAGE_NOTE)
    A = stored["adapters"]

    print("\n== S1 -- a thrown error whose message names BYDAY, decided by two month lengths")
    for l, g, d, r, n, t in PROBES:
        if g != "S1":
            continue
        print("\n  %-9s %s  %s\n    %s" % (l, d[:8], r, t))
        for name in ("icaljs", "dateutil", "sabre", "dmfs", "ical4j411", "ical4j430"):
            if name in A:
                print("      %-10s %s" % (name, show(A[name].get(l), n)))

    print("\n== S2 -- the month lattice is on the wrong INTERVAL phase")
    print("  'phase' = month offsets from DTSTART's month, mod INTERVAL. Correct is [0].")
    for l, g, d, r, n, t in PROBES:
        if g != "S2":
            continue
        ds = datetime.datetime.strptime(d, "%Y%m%dT%H%M%S")
        iv = int(parse_rrule(r).get("INTERVAL", 1))
        print("\n  %-9s %s  %s\n    %s" % (l, d[:8], r, t))
        for name in ("icaljs", "dateutil"):
            if name in A:
                print("      %-10s phase %-8s %s"
                      % (name, phase_of(A[name].get(l), ds, iv), show(A[name].get(l), n)))

    print("\n== controls. Any failure here refutes the characterisation.")
    for l, g, d, r, n, t in PROBES:
        if g != "C":
            continue
        ds = datetime.datetime.strptime(d, "%Y%m%dT%H%M%S")
        iv = int(parse_rrule(r).get("INTERVAL", 1))
        print("\n  %-13s %s  %s\n    %s" % (l, d[:8], r, t))
        for name in ("icaljs", "dateutil"):
            if name in A:
                print("      %-10s phase %-8s %s"
                      % (name, phase_of(A[name].get(l), ds, iv), show(A[name].get(l), n)))

    print("\n== S1's grid: 12 DTSTART months x 7 weekdays, BYMONTHDAY=-1, INTERVAL=3")
    print("  Predicted from the anchor month's length vs the landing month's length ALONE.")
    print("  R = ical.js rejects, . = accepted;  ! marks a prediction that missed.")
    gi = stored.get("grid_icaljs", {})
    gd = stored.get("grid_dateutil", {})
    print("        " + "  ".join("%-3s" % w for w in GRID_DOWS))
    ok = bad = firstok = firstbad = 0
    badlist = []
    for m in range(1, 13):
        ay, am = anchor_month(datetime.date(GRID_YEAR, m, 15), -1)
        row = []
        for w in GRID_DOWS:
            key = "G-%02d-%s" % (m, w)
            v = gi.get(key)
            act = bool(v and "error" in v)
            pred = grid_predict(m, w)
            hit = act == pred["rejected"]
            ok, bad = ok + hit, bad + (not hit)
            if not hit:
                badlist.append(key)
            mark = "R" if act else "."
            if not hit:
                mark += "!"
            if not act and v and v.get("occurrences"):
                firstok += (v["occurrences"][0][:8] == pred["first"])
                firstbad += (v["occurrences"][0][:8] != pred["first"])
            row.append("%-3s" % mark)
        print("  %02d/%-2s %s   (anchored in %04d-%02d, %d days)"
              % (m, dim(GRID_YEAR, m), "  ".join(row), ay, am, dim(ay, am)))
    print("\n  rejection predicted correctly on %d of %d grid cells; missed %d %s"
          % (ok, ok + bad, bad, " ".join(badlist) or ""))
    print("  and on the accepted cells the FIRST OCCURRENCE is predicted exactly"
          " on %d, missed %d" % (firstok, firstbad))
    nrej = sum(1 for k, v in gi.items() if "error" in v)
    ndrej = sum(1 for k, v in gd.items() if "error" in v)
    print("  ical.js rejects %d of %d; the reference rejects %d."
          % (nrej, len(gi), ndrej))

    print("\n== the corpus cases this finding claims")
    ci, cd = stored.get("corpus_icaljs", {}), stored.get("corpus_dateutil", {})
    agree = disagree = 0
    phase_hit = phase_miss = 0
    misses = []
    for c, p in scope:
        iv = int(p.get("INTERVAL", 1))
        ds = datetime.datetime.strptime(c["dtstart"], "%Y%m%dT%H%M%S")
        ay, am = anchor_month(ds.date(), int(p["BYMONTHDAY"].split(",")[0]))
        shift = month_offset(ay, am, ds.year, ds.month)
        pi, pd = phase_of(ci.get(c["id"]), ds, iv), phase_of(cd.get(c["id"]), ds, iv)
        same = ci.get(c["id"], {}).get("occurrences") == cd.get(c["id"], {}).get("occurrences")
        agree, disagree = agree + same, disagree + (not same)
        if iv > 1 and pi is not None:
            want = [shift % iv]
            if pi == want:
                phase_hit += 1
            else:
                phase_miss += 1
                misses.append("%s pred %s got %s" % (c["id"][:12], want, pi))
        print("  %-12s %s  %-58s iv=%-2d shift=%-3d icaljs phase %-6s ref phase %-6s %s"
              % (c["id"][:12], c["dtstart"][:8], c["rrule"], iv, shift,
                 pi, pd, "AGREE" if same else "differs"))
    print("\n  in-scope corpus cases: %d of %d   agree with reference: %d, differ: %d"
          % (len(scope), len(cases), agree, disagree))
    print("  where INTERVAL > 1, the predicted phase -shift mod INTERVAL is exact on"
          " %d, missed %d" % (phase_hit, phase_miss))
    for m in misses:
        print("    MISS " + m)

    if os.path.exists(RESID):
        un = set(json.load(open(RESID))["ids"]["unexplained"])
        hits = sorted(c["id"] for c, _ in scope if c["id"] in un)
        print("\n-- against 074's unattributed residual")
        print("  in scope and unattributed: %d  %s"
              % (len(hits), " ".join(i[:12] for i in hits)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

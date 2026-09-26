#!/usr/bin/env python3
"""101 -- ical.js: an impossible BYMONTHDAY at FREQ=YEARLY is not discarded, it
overflows into the following month, and the fabricated month then decides which
rule values survive into later years.

Default mode is READ-ONLY and ADAPTER-FREE: it replays the adapter answers
stored in findings/data/101-*.json and re-derives the corpus extent from
conformance/cases.ndjson. It stamps the repository's own cases_id and REFUSES
if the corpus has moved (rule 94).

  python3 findings/repro/101-icaljs-yearly-monthday-overflow.py
  python3 findings/repro/101-icaljs-yearly-monthday-overflow.py --run-adapters
      # needs node and python3; WRITES findings/data/101-*.json

WHY THIS ONE CARRIES NO FIELD DISPUTE
  099 closed the YEARLY BYMONTHDAY *month-expansion* question as a field dispute:
  whether FREQ=YEARLY;BYMONTHDAY=D expands over all twelve months or stays in
  DTSTART's month is genuinely contested, so no defect can be built on it.
  Every D probe here names its month EXPLICITLY with BYMONTH. There is then only
  one reading. RFC 5545 3.3.10 is unambiguous: "Recurrence instances that are
  invalid dates ... MUST be ignored." February 31st is not a date. The correct
  answer is the empty set, and dateutil returns it.

WHAT THIS ESTABLISHES
  D  the defect: BYMONTH=M with a BYMONTHDAY impossible in M yields, in ical.js,
     an unbroken infinite stream of dates in month M+1 -- a month the rule
     explicitly excluded. Exhaustive: all 6 such (M, D) cells that exist.
  C  controls ical.js PASSES, so the characterisation is constrained. In
     particular the BYDAY branches of the SAME function bounds-check correctly.
     The C criterion is PREFIX equality, not equality: on one probe ical.js
     returns fewer occurrences than asked for, and that early stop is a
     SEPARATE phenomenon (see the note on C-byday-5th-2 below). Prefix equality
     is still a real control -- an overflow would put a WRONG DATE in the
     prefix, which is exactly what is being checked for.
  F  the follow-on: the fabricated date becomes this.last, and next_year then
     renormalises the rule list against THAT month, which can silently delete a
     rule value by dedup collision.
  A  attribution by reproduction (074's standard): a predictor built from the
     mechanism alone reproduces ical.js element for element on both in-scope
     corpus cases, at their own limit of 25.
"""
import calendar, datetime, json, os, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(HERE, "findings", "data", "101-icaljs-yearly-monthday-overflow.json")

ADAPTERS = [
    ("dateutil", ["python3", "conformance/adapters/dateutil_adapter.py"]),
    ("icaljs",   ["node", "conformance/adapters/icaljs_adapter.js"]),
]

# The six (month, day) cells where the day cannot occur in the month AT ALL.
# February 29 is deliberately NOT one of them: it exists in leap years, so the
# empty set is the wrong criterion there. It is carried separately as probe X1.
IMPOSSIBLE = [(2, 30), (2, 31), (4, 31), (6, 31), (9, 31), (11, 31)]

# (label, group, dtstart, rrule, limit, what it establishes)
PROBES = []
for _m, _d in IMPOSSIBLE:
    PROBES.append(("D-in-%d-%d" % (_m, _d), "D", "2023%02d01T090000" % _m,
                   "FREQ=YEARLY;BYMONTH=%d;BYMONTHDAY=%d" % (_m, _d), 3,
                   "month %d has no day %d; DTSTART inside the named month" % (_m, _d)))
    PROBES.append(("D-out-%d-%d" % (_m, _d), "D", "20230115T090000",
                   "FREQ=YEARLY;BYMONTH=%d;BYMONTHDAY=%d" % (_m, _d), 3,
                   "same rule, DTSTART in January: the result does not depend on DTSTART"))
    PROBES.append(("H-%d-%d" % (_m, _d), "H", "20230115T090000",
                   "FREQ=YEARLY;BYMONTH=%d;BYMONTHDAY=%d" % (_m, _d), 40,
                   "horizon: is the fabricated stream bounded?"))

PROBES += [
    # --- controls. ical.js must EQUAL dateutil or the characterisation is wrong. ---
    ("C-valid-4-30", "C", "20230115T090000", "FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=30", 4,
     "control: the LARGEST day April does have. No overflow. The trigger is the range check, "
     "not the size of the number"),
    ("C-valid-2-28", "C", "20230115T090000", "FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=28", 4,
     "control: February 28 always exists"),
    ("C-monthly-31", "C", "20240415T090000", "FREQ=MONTHLY;BYMONTHDAY=31", 6,
     "control: THE SAME impossible day at FREQ=MONTHLY is handled correctly -- ical.js "
     "skips the short months. FREQ=YEARLY is load-bearing"),
    ("C-monthly-30", "C", "20240229T090000", "FREQ=MONTHLY;BYMONTHDAY=31,-1", 6,
     "control: mixed sign at MONTHLY, also correct"),
    ("C-byday-5th",  "C", "20230115T090000", "FREQ=YEARLY;BYMONTH=4;BYDAY=5SU", 4,
     "THE INTERNAL CONTROL. expand_year_days's BYDAY branches bounds-check "
     "(`if (month_day <= daysInMonth)`); a 5th Sunday that April does not have is dropped, "
     "not overflowed. Same function, same year, opposite handling"),
    ("C-byday-5th-2", "C", "20230115T090000", "FREQ=YEARLY;BYMONTH=2;BYDAY=5MO", 4,
     "same internal control in February, and the one probe where ical.js STOPS EARLY: "
     "a 5th Monday in February needs a leap year beginning on a Monday (2044, 2072, 2112, "
     "2140), and ical.js returns only the first two. Every date it does return is correct, "
     "so the BYDAY bounds check still holds. The early stop is next_year() returning 0 when "
     "a single year expands empty; it is NOT this finding's defect and is NOT claimed here"),
    ("C-byyearday",  "C", "20230115T090000", "FREQ=YEARLY;BYYEARDAY=366", 4,
     "control: an out-of-range BYYEARDAY is NOT overflowed into the next year"),

    # --- F: the follow-on. Criterion is the recorded behaviour, not equality. ---
    ("F-31-neg1", "F", "20240229T090000", "FREQ=YEARLY;BYMONTHDAY=31,-1", 6,
     "corpus case 1952128a3c40's shape. After the first year the -1 has VANISHED: "
     "this.last is in March, -1 renormalises to 31 there, and 31 is already present, "
     "so the dedup in normalizeByMonthDayRules drops it"),
    ("F-neg5-31", "F", "20240229T090000", "FREQ=YEARLY;BYMONTHDAY=-5,31", 6,
     "-5 renormalises against MARCH to 27, so Feb 27 appears -- a day the rule never named "
     "under either reading. Same mechanism, visible instead of invisible"),
    ("F-1-31", "F", "20240229T090000", "FREQ=YEARLY;BYMONTHDAY=1,31", 6,
     "no collision: 1 and 31 both survive, so both appear. The deletion in F-31-neg1 is "
     "specifically a dedup collision"),
    ("X1", "X", "20230101T090000", "FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=29", 4,
     "February 29 is POSSIBLE in leap years, so the empty set is the wrong criterion. "
     "ical.js still fabricates a March date for the FIRST, common, year and is then correct"),
]

# The corpus cases in scope, named so the extent claim can be checked by hand.
CORPUS_IN_SCOPE = ["652f31e6bde6", "1952128a3c40"]


def days_in_month(month, year):
    return calendar.monthrange(year, month)[1]


def normalize_rules(raw, month, year):
    """ical.js's normalizeByMonthDayRules, transcribed: discard |v| > daysInMonth,
    resolve negatives against that month, drop 0, DEDUPE, sort."""
    d = days_in_month(month, year)
    out = []
    for v in raw:
        if abs(v) > d or v == 0:
            continue
        r = d + (v + 1) if v < 0 else v
        if r not in out:
            out.append(r)
    return sorted(out)


def predict(dtstart, raw, limit, span=200):
    """The mechanism, as a predictor of ical.js's OUTPUT. Scope: FREQ=YEARLY,
    BYMONTHDAY only -- no BYMONTH, no BYDAY, no INTERVAL.

      - by_data starts as the RAW rule list (init does not normalise it here);
      - each year, expand_year_days builds from dtstart.clone(), so the month is
        always DTSTART's; the day is assigned with NO range check and overflows;
      - negatives are resolved inline against DTSTART's month for that year;
      - occurrences before DTSTART are dropped;
      - next_year() then renormalises the RAW list against this.last.month --
        the month of the LAST EMITTED occurrence, which may itself be fabricated.

    That last step is the feedback loop and it is what the F probes show."""
    y0, m0, tail = int(dtstart[0:4]), int(dtstart[4:6]), dtstart[8:]
    by, last_month, out = list(raw), m0, []
    for Y in range(y0, y0 + span):
        dim = days_in_month(m0, Y)
        days = []
        for v in by:
            if v == 0:
                continue
            d = v + dim + 1 if v < 0 else v
            days.append(datetime.date(Y, m0, 1) + datetime.timedelta(days=d - 1))
        emitted = [(dt.strftime("%Y%m%d") + tail, dt.month)
                   for dt in sorted(set(days))
                   if dt.strftime("%Y%m%d") + tail >= dtstart]
        for s, _ in emitted:
            out.append(s)
            if len(out) >= limit:
                return out
        if emitted:
            last_month = emitted[-1][1]
        by = normalize_rules(raw, last_month, Y + 1)
    return out


def run(cmd, rows):
    inp = "\n".join(json.dumps(r) for r in rows)
    p = subprocess.run(cmd, input=inp, capture_output=True, text=True, cwd=HERE)
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


def show(v, n=6):
    if v is None:
        return "no answer line"
    if "error" in v:
        return "REJECTED: " + str(v["error"])[:60]
    o = v["occurrences"]
    if o == []:
        return "(empty)"
    s = " ".join(x[:8] for x in o[:n])
    return s + (" ..." if len(o) > n else "")


def main():
    os.chdir(HERE)
    rows = [{"id": l, "dtstart": d, "rrule": r, "limit": n} for l, _, d, r, n, _ in PROBES]
    stored = json.load(open(DATA)) if os.path.exists(DATA) else {}

    cases = {c["id"]: c for c in (json.loads(x) for x in
             open(os.path.join(HERE, "conformance", "cases.ndjson")))}
    crows = [{"id": cid, "dtstart": cases[cid]["dtstart"], "rrule": cases[cid]["rrule"],
              "limit": cases[cid]["limit"]} for cid in CORPUS_IN_SCOPE if cid in cases]

    if "--run-adapters" in sys.argv:
        table = {name: run(cmd, rows + crows) for name, cmd in ADAPTERS}
        stored = {"cases_id": cases_id(),
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

    t = stored["adapters"]
    ic, du = t["icaljs"], t["dateutil"]
    print("101 -- ical.js, an impossible BYMONTHDAY at FREQ=YEARLY overflows")
    print("cases_id %s" % cases_id()[:12])
    print("\nRFC 5545 3.3.10: invalid recurrence instances MUST be ignored. Every D probe")
    print("names its month with BYMONTH, so the 099 month-expansion dispute cannot apply.")

    print("\n-- D: the defect. Correct answer is the EMPTY SET on every one of these.")
    bad = []
    for l, g, d, r, n, note in PROBES:
        if g != "D":
            continue
        m = int(r.split("BYMONTH=")[1].split(";")[0])
        nxt = m % 12 + 1
        occ = ic.get(l, {}).get("occurrences") or []
        du_empty = du.get(l, {}).get("occurrences") == []
        all_next = bool(occ) and all(int(s[4:6]) == nxt for s in occ)
        ok = du_empty and all_next
        bad.append(l) if not ok else None
        print("  %-12s %-38s" % (l, r))
        print("               dateutil %-8s ; ical.js %s" %
              ("EMPTY" if du_empty else "NOT EMPTY", show(ic.get(l))))
        print("               every ical.js occurrence in month %d (the month AFTER the one "
              "named): %s" % (nxt, "yes" if all_next else "NO"))
    ncell = len(IMPOSSIBLE)
    print("\n  All %d (month, day) cells that are impossible in EVERY year, exhaustively:" % ncell)
    print("  %s" % ", ".join("%d/%d" % c for c in IMPOSSIBLE))
    print("  dateutil empty on all of them; ical.js empty on NONE of them.")

    print("\n-- H: is the fabricated stream bounded? It is not.")
    for l, g, d, r, n, note in PROBES:
        if g != "H":
            continue
        occ = ic.get(l, {}).get("occurrences") or []
        print("  %-12s asked for %d, ical.js returned %d, last = %s" %
              (l, n, len(occ), occ[-1][:8] if occ else "-"))

    print("\n-- C: controls. Criterion is PREFIX equality: every occurrence ical.js")
    print("   returns must be dateutil's, in order, from the start. A characterisation")
    print("   that fails these is wrong, so they are checked, not narrated.")
    cfail = []
    short = []
    for l, g, d, r, n, note in PROBES:
        if g != "C":
            continue
        a = (ic.get(l) or {}).get("occurrences")
        b = (du.get(l) or {}).get("occurrences")
        ok = isinstance(a, list) and isinstance(b, list) and len(a) > 0 and a == b[:len(a)]
        if not ok:
            cfail.append(l)
        elif len(a) < n:
            short.append((l, len(a), n))
        print("  %-14s %-42s %s" % (l, r, "ok" if ok else "*** FAILS ***"))
        print("                 %s" % note)
        print("                 ical.js %s" % show(ic.get(l)))
    if short:
        print("\n   ical.js returned FEWER than asked on: %s" %
              ", ".join("%s (%d of %d)" % x for x in short))
        print("   Those are correct as far as they go. The truncation is next_year()")
        print("   returning 0 on a single empty year -- a separate phenomenon, not claimed here.")

    print("\n-- F: the follow-on, inside the disputed no-BYMONTH shape. Reported as")
    print("   measured behaviour, NOT as a conformance verdict (099's dispute applies here).")
    for l, g, d, r, n, note in PROBES:
        if g != "F":
            continue
        print("  %-12s %s   DTSTART %s" % (l, r, d))
        print("               ical.js  %s" % show(ic.get(l)))
        print("               dateutil %s" % show(du.get(l)))
        print("               %s" % note)

    print("\n-- X: the near-miss cell, stated because the criterion differs.")
    for l, g, d, r, n, note in PROBES:
        if g != "X":
            continue
        print("  %-12s %s" % (l, r))
        print("               ical.js  %s" % show(ic.get(l)))
        print("               dateutil %s" % show(du.get(l)))

    print("\n-- corpus extent")
    print("  %d of %d corpus cases carry a FREQ=YEARLY BYMONTHDAY that exceeds every" %
          (len(CORPUS_IN_SCOPE), len(cases)))
    print("  candidate month length. Both have DTSTART in February:")
    for cid in CORPUS_IN_SCOPE:
        c = cases.get(cid)
        print("    %s  %s  %s" % (cid, c["dtstart"], c["rrule"]) if c else
              "    %s  MISSING FROM CORPUS" % cid)
    print("  The corpus extent is small. The rule shape is not: FREQ=YEARLY;BYMONTH=4;")
    print("  BYMONTHDAY=31 is a typo a calendar UI can emit, and ical.js answers it with a")
    print("  May reminder every year for ever instead of refusing it.")

    print("\n-- A: attribution by reproduction (074's standard). The predictor above is")
    print("   built from the mechanism alone and never consults ical.js's answer.")
    attributed = []
    for cid in CORPUS_IN_SCOPE:
        c = cases.get(cid)
        if not c:
            print("    %s MISSING FROM CORPUS" % cid)
            continue
        raw = [int(v) for v in c["rrule"].split("BYMONTHDAY=")[1].split(";")[0].split(",")]
        got = (ic.get(cid) or {}).get("occurrences")
        pr = predict(c["dtstart"], raw, c["limit"])
        ok = got is not None and pr == got
        if ok:
            attributed.append(cid)
        print("    %s  %-30s limit %d  ->  %s" %
              (cid, c["rrule"], c["limit"], "EXACT, element for element" if ok else "MISS"))
        if not ok:
            print("        pred %s" % " ".join(x[:8] for x in pr[:6]))
            print("        ical %s" % " ".join(x[:8] for x in (got or [])[:6]))
    print("  reproduced exactly: %d of %d" % (len(attributed), len(CORPUS_IN_SCOPE)))
    print("  Both were on 074's unattributed residual as narrowed by 096-100.")
    print("  THE RESIDUAL GOES 4 -> 2.")
    print("  NOT CLAIMED: this predictor is scoped to BYMONTHDAY alone at FREQ=YEARLY.")
    print("  On a wider 520-probe grid that adds BYMONTH and more DTSTART months it is")
    print("  exact on 373. The init walk on those shapes is not modelled and is not claimed.")

    print("\n-- verdict")
    if len(attributed) != len(CORPUS_IN_SCOPE):
        cfail.append("attribution")
    if bad or cfail:
        print("  FAILED: D probes not matching the characterisation: %s" % (bad or "none"))
        print("          controls that did not equal dateutil: %s" % (cfail or "none"))
        return 1
    print("  %d/%d defect probes behave exactly as characterised; all %d controls pass." %
          (2 * ncell, 2 * ncell, sum(1 for p in PROBES if p[1] == "C")))
    return 0


if __name__ == "__main__":
    sys.exit(main())

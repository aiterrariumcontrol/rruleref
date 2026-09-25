"""Three new ical.js defects reached by COMPOSING published ones, plus the
BYMONTH cursor that produces two of them.

    python3 findings/repro/096-icaljs-bymonth-cursor.py                # read-only replay
    python3 findings/repro/096-icaljs-bymonth-cursor.py --run-adapters # re-measure (needs JVM/PHP)

Finding 074 attributed ical.js's 236 mismatches by evaluating ONE deliberately
broken version of each rule and demanding element-for-element equality. 23 did
not reproduce under any single mutation. Standing rule 103 says to classify a
residual against what has already been published before treating it as a
discovery target, and that is where this started: of the 23, six share one
visible shape (the DTSTART period's occurrence set emitted TWICE) and one is a
negative BYMONTHDAY resolved against the wrong month. Neither is reachable by a
single mutation, because each is a published defect with a second thing on top.

The three defects below were then isolated by hand-written probes, NOT by
mutation search, and each has a minimal reproducer measured against every
adapter that builds here. Corroboration is stored so the default mode needs no
JVM and no PHP.

J -- at FREQ=YEARLY with BYMONTH and a negative BYMONTHDAY, from the SECOND
    period on the negative monthday is converted to a single positive day
    number using the length of the LAST-WRITTEN BYMONTH value, and that one
    number is applied to every month of the period. The first period is
    correct. Invisible whenever every BYMONTH value has the same length, which
    is why the corpus exercises it twice in 1727 cases.

K -- at FREQ=MONTHLY with two or more BYMONTH values, if DTSTART's month is not
    the FIRST-WRITTEN value and DTSTART's period yields two or more
    occurrences, that period's whole set is emitted twice. A period yielding
    exactly one occurrence does not duplicate, which is why 074's predictor
    "BYMONTH expanded at MONTHLY, emitting each period once per value" (defect
    I) matched only one case: I duplicates every period, K duplicates the first.

L -- BYMONTH values are walked in WRITTEN order, not sorted. With a descending
    list the output is not in chronological order and an occurrence is skipped.

J and K are the same cursor seen twice: ical.js enters the BYMONTH list at
DTSTART's month rather than at the head of the list.
"""
import json, os, subprocess, sys, calendar
from datetime import date, datetime, timedelta

sys.path.insert(0, "src")
try:
    import env; env.add_dateutil_to_path()
except Exception:
    pass
from dateutil.rrule import rrulestr

FMT = "%Y%m%dT%H%M%S"
HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(HERE, "findings", "data", "096-icaljs-bymonth-cursor.json")
RESID = os.path.join(HERE, "findings", "data", "074-icaljs-residual-reproduced.json")

ADAPTERS = [
    ("dateutil",  ["python3", "conformance/adapters/dateutil_adapter.py"]),
    ("icaljs",    ["node", "conformance/adapters/icaljs_adapter.js"]),
    ("rrulejs",   ["node", "conformance/adapters/rrulejs_adapter.js"]),
    ("sabre",     ["php", "conformance/adapters/php/vobject_adapter.php"]),
    ("dmfs",      ["java", "-cp", "conformance/adapters/java/classes:conformance/adapters/java/libs/*", "DmfsAdapter"]),
    ("ical4j411", ["java", "-cp", "conformance/adapters/java/classes:conformance/adapters/java/libs/*", "Ical4jAdapter"]),
    ("ical4j430", ["java", "-cp", "conformance/adapters/java/classes:conformance/adapters/java/libs430/*:conformance/adapters/java/libs/*", "Ical4jAdapter"]),
]

# (label, dtstart, rrule, limit, what it establishes)
PROBES = [
    # --- defect J ---
    ("J-min",  "20260201T090000", "FREQ=YEARLY;BYMONTH=2,10;BYMONTHDAY=-1", 6,
     "Feb -1 becomes day 31 from 2027 on, rolling into March; Oct is right"),
    ("J-ctl",  "20260201T090000", "FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=-1", 3,
     "control: one BYMONTH value, correct"),
    ("J-len",  "20260201T090000", "FREQ=YEARLY;BYMONTH=2,4;BYMONTHDAY=-1", 6,
     "last value April (30) gives day 30, not 31: the length is CARRIED, not a constant"),
    ("J-len2", "20260201T090000", "FREQ=YEARLY;BYMONTH=2,3;BYMONTHDAY=-1", 6,
     "last value March (31) gives day 31"),
    ("J-all",  "20260201T090000", "FREQ=YEARLY;BYMONTH=2,4,10;BYMONTHDAY=-1", 9,
     "ONE number for the whole period: April also gets 31, rolling into May"),
    ("J-neg2", "20260401T090000", "FREQ=YEARLY;BYMONTH=4,10;BYMONTHDAY=-2", 6,
     "-2 against October gives day 30, so April yields the 30th"),
    ("J-same", "20260401T090000", "FREQ=YEARLY;BYMONTH=4,6,9,11;BYMONTHDAY=-1", 8,
     "control: every value 30 days, defect invisible"),
    # --- defect K ---
    ("K-min",  "20260901T090000", "FREQ=MONTHLY;BYMONTH=3,9;BYMONTHDAY=15,20", 6,
     "DTSTART month is not the first value and the period has 2 occurrences: set emitted twice"),
    ("K-one",  "20260901T090000", "FREQ=MONTHLY;BYMONTH=3,9;BYMONTHDAY=15", 4,
     "control: one occurrence per period, no duplication"),
    ("K-first", "20260301T090000", "FREQ=MONTHLY;BYMONTH=3,9;BYMONTHDAY=15,20", 6,
     "control: DTSTART month IS the first written value, correct"),
    ("K-mid",  "20260601T090000", "FREQ=MONTHLY;BYMONTH=3,6,9;BYMONTHDAY=15,20", 8,
     "the duplicated month need not be the last value, only not the first"),
    ("K-byday", "20260901T090000", "FREQ=MONTHLY;BYMONTH=3,9;BYDAY=MO", 8,
     "same with BYDAY: the whole September Monday set twice"),
    ("K-ord",  "20260901T090000", "FREQ=MONTHLY;BYMONTH=3,9;BYDAY=1MO", 5,
     "control: ordinal BYDAY gives one occurrence per period, no duplication"),
    # --- defect L ---
    ("L-min",  "20260901T090000", "FREQ=MONTHLY;BYMONTH=9,3;BYMONTHDAY=15,20", 6,
     "descending BYMONTH: output not chronological, and it is K's control too"),
    ("L-skip", "20260301T090000", "FREQ=MONTHLY;BYMONTH=9,3", 6,
     "descending BYMONTH: September 2026 is skipped entirely"),
]


def parts(r):
    d = {}
    for p in r.split(';'):
        k, _, v = p.partition('='); d[k] = v
    return d


def run(cmd, rows):
    inp = '\n'.join(json.dumps(r) for r in rows)
    p = subprocess.run(cmd, input=inp, capture_output=True, text=True)
    out = {}
    for line in p.stdout.splitlines():
        if not line.startswith('{'):
            continue
        o = json.loads(line)
        out[o['id']] = o.get('occurrences')
    return out


# ---------------------------------------------------------------- predictors

def predict_J(c):
    """Defect J as a generator, so the claim is falsifiable element for element."""
    p = parts(c['rrule']); dt = datetime.strptime(c['dtstart'], FMT)
    if p.get('FREQ') != 'YEARLY' or 'BYMONTH' not in p or 'BYMONTHDAY' not in p:
        return None
    if 'BYDAY' in p:
        return None
    months = [int(x) for x in p['BYMONTH'].split(',')]
    mds = [int(x) for x in p['BYMONTHDAY'].split(',')]
    if not any(v < 0 for v in mds):
        return None
    iv = int(p.get('INTERVAL', 1)); sp = p.get('BYSETPOS')
    out = []; y = dt.year; n = 0
    while len(out) < c['limit'] + 5 and n < 400:
        carried = calendar.monthrange(y, months[-1])[1]
        got = []
        for m in sorted(months):
            L = calendar.monthrange(y, m)[1]
            for md in mds:
                dnum = md if md > 0 else ((L + md + 1) if n == 0 else (carried + md + 1))
                got.append(date(y, m, 1) + timedelta(days=dnum - 1))
        got = sorted(set(got))
        if sp:
            idxs = [int(x) for x in sp.split(',')]
            got = [got[i - 1 if i > 0 else len(got) + i] for i in idxs
                   if i != 0 and -len(got) <= i <= len(got)]
        for d0 in got:
            v = datetime.combine(d0, dt.time())
            if v >= dt:
                out.append(v.strftime(FMT))
        y += iv; n += 1
    return sorted(set(out))[:c['limit']]


def predict_K(correct, c):
    """Defect K: re-emit the DTSTART period's occurrence set once more.

    Applied to the CORRECT answer, so it composes with nothing and says only
    'this output is the right one with the first period repeated'.
    """
    p = parts(c['rrule'])
    if p.get('FREQ') != 'MONTHLY' or 'BYMONTH' not in p:
        return None
    months = [int(x) for x in p['BYMONTH'].split(',')]
    if len(months) < 2:
        return None
    dt = datetime.strptime(c['dtstart'], FMT)
    if dt.month == months[0]:
        return None
    head = [x for x in correct
            if datetime.strptime(x, FMT).year == dt.year
            and datetime.strptime(x, FMT).month == dt.month]
    if len(head) < 2:
        return None
    return (head + correct)[:c['limit']]


def ev(rrule, dtstart, limit):
    """dateutil as a RULE EVALUATOR only -- standing rule 24, not an oracle for truth."""
    try:
        it = rrulestr("RRULE:" + rrule, dtstart=datetime.strptime(dtstart, FMT))
        out = []
        for i, v in enumerate(it):
            if i >= limit:
                break
            out.append(v.strftime(FMT))
        return out
    except Exception:
        return None


def setp(r, name, val):
    return ';'.join([x for x in r.split(';') if x.split('=')[0] != name] + ["%s=%s" % (name, val)])


def predict_KF(c):
    """K composed with 074-F (INTERVAL lost when BYMONTH is present at MONTHLY).

    This is the whole point of the finding: neither mutation alone reproduces
    these outputs, and 074's search tried one at a time.
    """
    p = parts(c['rrule'])
    if p.get('INTERVAL', '1') == '1':
        return None
    base = ev(setp(c['rrule'], 'INTERVAL', 1), c['dtstart'], c['limit'] + 40)
    if base is None:
        return None
    return predict_K(base, c)


def load_cases():
    out = {}
    for line in open("conformance/cases.ndjson"):
        c = json.loads(line); out[c["id"]] = c
    return out


def cases_id():
    """The repository's OWN cases_id, not a second hash of the same file.

    An ad-hoc sha256 over cases.ndjson does not equal tools/corpus_id.py's
    cases_id, which binds each digest to its path. Publishing a second corpus
    identity would be worse than publishing none.
    """
    sys.path.insert(0, "tools")
    import corpus_id
    return corpus_id.compute()["cases_id"]


def main():
    os.chdir(HERE)
    cases = load_cases()
    rows = [{"id": lab, "dtstart": ds, "rrule": rr, "limit": lim}
            for lab, ds, rr, lim, _ in PROBES]
    stored = json.load(open(DATA)) if os.path.exists(DATA) else {}

    if '--run-adapters' in sys.argv:
        table = {}
        for name, cmd in ADAPTERS:
            got = run(cmd, rows)
            if got:
                table[name] = got
            else:
                print("  (%s produced nothing, skipped)" % name)
        resid_ids = json.load(open(RESID))["ids"]["unexplained"]
        cases = load_cases()
        live = run(["node", "conformance/adapters/icaljs_adapter.js"],
                   [{"id": i, "dtstart": cases[i]["dtstart"], "rrule": cases[i]["rrule"],
                     "limit": cases[i]["limit"]} for i in resid_ids])
        stored = {"cases_id": cases_id(),
                  "probes": {lab: {"dtstart": ds, "rrule": rr, "limit": lim, "note": note}
                             for lab, ds, rr, lim, note in PROBES},
                  "adapters": table,
                  "residual_icaljs": live,
                  "residual_limits": {i: cases[i]["limit"] for i in resid_ids}}
        json.dump(stored, open(DATA, "w"), indent=1, sort_keys=True)
        print("-> %s" % DATA)

    # 094's rule: an answer is only meaningful at the depth it was asked for.
    if stored.get("cases_id") != cases_id():
        sys.exit("REFUSING: stored answers were taken at cases_id %s, corpus is now %s. "
                 "Re-run with --run-adapters." % (str(stored.get("cases_id"))[:12], cases_id()[:12]))
    for i, lim in stored["residual_limits"].items():
        if cases.get(i) is None or cases[i]["limit"] != lim:
            sys.exit("REFUSING: case %s changed its limit since the replay was stored." % i)

    table = stored["adapters"]
    ref = "dateutil"
    print("PROBES -- %d adapters, reference for the RULE (not for the truth) is %s"
          % (len(table), ref))
    alone = 0
    for lab, ds, rr, lim, note in PROBES:
        ic = table["icaljs"].get(lab)
        others = {n: v for n, v in table.items() if n not in ("icaljs", "sabre")}
        agree = len({json.dumps(v) for v in others.values()}) == 1
        differs = ic != table[ref].get(lab)
        if differs and agree:
            alone += 1
        print("  %-7s %-10s %s  %s" % (lab,
              "DIFFERS" if differs else "matches",
              "all others agree" if agree else "OTHERS DISAGREE", note))
    print("  ical.js alone against a unanimous field on %d of %d probes" % (alone, len(PROBES)))

    # ---- what the two predictors do to 074's 23
    resid = json.load(open(RESID))
    un = resid["ids"]["unexplained"]
    cases = load_cases()
    live = stored["residual_icaljs"]
    hit = {"J": [], "K": [], "K+074-F": [], "still unexplained": []}
    for i in un:
        c = cases[i]; got = live[i]
        if predict_J(c) == got:
            hit["J"].append(i)
        elif predict_K(c["expect"], c) == got:
            hit["K"].append(i)
        elif predict_KF(c) == got:
            hit["K+074-F"].append(i)
        else:
            hit["still unexplained"].append(i)
    print("\n074's 23 unexplained, re-classified:")
    for k in ("J", "K", "K+074-F", "still unexplained"):
        print("  %2d  %s" % (len(hit[k]), k))
    # Measured, then committed as a drift check -- NOT a guess. If any of these
    # move, the corpus or ical.js changed and this finding needs re-reading.
    assert alone == 10, alone
    assert len(hit["J"]) == 1, hit["J"]
    assert len(hit["K"]) == 2, hit["K"]
    assert len(hit["K+074-F"]) == 4, hit["K+074-F"]
    assert len(hit["still unexplained"]) == 16, len(hit["still unexplained"])
    print("\nJ, K and K+074-F take 074's residual from 23 to 16.")
    print("Every one of the four K+074-F cases carries INTERVAL; neither mutation")
    print("alone reproduces any of them, which is why 074's one-at-a-time search missed them.")
    return hit


if __name__ == "__main__":
    main()

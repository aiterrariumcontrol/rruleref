"""Run RFC 5545's own examples against implementations, or classify the answers.

`corpus/rfc5545-examples.json` holds the 39 worked examples of RFC 5545
section 3.8.5.3, extracted by program from the hashed RFC text (42 RRULEs --
three examples give two equivalent rules). They are the most authoritative
cases that exist for this problem, and until this audit not one of them had
been shown to an implementation on `conformance/RESULTS.md`.

The reason was `PROTOCOL.md`'s rule that the corpus is floating time: every
example carries `TZID:America/New_York`, so all 39 were excluded. That rule is
right about what it defends against and wrong about how much it excluded.
RRULE expansion is local-calendar arithmetic -- a DST transition moves the UTC
offset of an occurrence, never its local time -- so an example is timezone
dependent only where the *rule text itself* names an absolute instant, which
here means `UNTIL=...Z`. Measured rather than argued: `naive.expand`, given the
example's local `DTSTART` and nothing else, reproduces the RFC's printed
occurrences for 41 of the 42 rules.

And the eight `UNTIL=...Z` rules are not a timezone problem either. RFC 5545
3.3.10 says, of `UNTIL`: "if the 'DTSTART' property is specified as a date with
local time, then the UNTIL rule part MUST also be specified as a date with
local time." Every `DTSTART` in this protocol is floating by construction, so
those eight are *prohibited* in the form the harness can pose them, and an
implementation's behaviour on a prohibited rule is not a conformance fact.
They are marked PROHIBITED here and excluded from the score, which leaves 34
scorable rules. The one rule where a floating reading changes the answer at all
(example 32, `FREQ=HOURLY;INTERVAL=3;UNTIL=19970902T210000Z`: 21:00Z is 17:00
local, and floating keeps an 18:00 occurrence the RFC does not print) is one of
the eight. So nothing in this case set is timezone dependent except by way of a
rule the RFC forbids. Thirty-nine examples were held off the board to guard
against a hazard that is not in them.

    python3 tools/audit_rfc_examples.py --emit > rfc_cases.ndjson
    TZ=UTC <adapter> < rfc_cases.ndjson > out.<name>.ndjson    # PROTOCOL.md
    python3 tools/audit_rfc_examples.py --classify out.*.ndjson

Each answer is classified against the RFC's own list:

    R    equals the RFC's printed occurrences
    F    equals the floating reading where that differs from the RFC's
    X    a third answer        ERR  the adapter refused the rule or crashed

and a PROHIBITED rule's answer is reported in its own column and scored by
nobody. Refusing such a rule is correct behaviour, not an error.

`limit` follows the same convention as the conformance harness: an example
whose recurrence set the RFC prints to its end is asked for one occurrence
more than it prints, so an implementation that runs past the end fails.

Two controls run on every `--classify`, and both must be clean before any row
below may be cited:

  * POSITIVE -- `naive.expand` reproduces the RFC's printed list on all 41
    timezone-independent rules, and on the timezone-dependent one returns the
    floating answer and not the RFC's. This pins the instrument and the
    timezone claim at the same time.
  * NEGATIVE -- the same lists shifted one day later are matched by nothing.
    A classifier that says "agrees" too easily fails here.

A missing answer, a refusal and a crash are all ERR. None never equals None.
"""
import argparse, datetime, hashlib, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
import naive  # noqa: E402

FMT = "%Y%m%dT%H%M%S"


def case_id(rrule, dtstart):
    return hashlib.sha256(
        ("%s\n%s" % (rrule, dtstart)).encode()).hexdigest()[:12]


def load_cases():
    """The 42 RFC 5545 3.8.5.3 rules as protocol cases, in document order."""
    path = os.path.join(REPO, "corpus", "rfc5545-examples.json")
    with open(path) as f:
        doc = json.load(f)
    cases, order = {}, []
    for n, e in enumerate(doc["examples"]):
        expect = [o["local"] for o in e["expected"]]
        prefix = e["expected_is_prefix_only"]
        for r in e["rrules"]:
            cid = case_id(r, e["dtstart"])
            if cid in cases:
                raise SystemExit("case_id collision on %s" % cid)
            cases[cid] = {
                "example": n,
                "desc": e["desc"],
                "rrule": r,
                "dtstart": e["dtstart"],
                "tzid": e["tzid"],
                "limit": len(expect) + (0 if prefix else 1),
                "expect_bound": "prefix" if prefix else "complete",
                "rfc": expect,
            }
            order.append(cid)
    for cid in order:
        c = cases[cid]
        c["floating"] = expand_naive(c["rrule"], c["dtstart"], c["limit"])
        c["tz_dependent"] = c["floating"] != c["rfc"]
        # 3.3.10: a floating DTSTART requires a floating UNTIL. Every DTSTART
        # in this protocol is floating, so a UTC UNTIL is prohibited here.
        c["prohibited"] = bool(re.search(r"(?:^|;)UNTIL=[^;]*Z\s*$|(?:^|;)UNTIL=[^;]*Z;",
                                         c["rrule"], re.I))
    return cases, order


def expand_naive(rrule, dtstart, limit):
    ds = datetime.datetime.strptime(dtstart, FMT)
    return [x.strftime(FMT) for x in naive.expand(rrule, ds, limit=limit)][:limit]


def shift_a_day(occs):
    """The negative control's wrong answer: every instant one day later."""
    out = []
    for o in occs:
        d = datetime.datetime.strptime(o, FMT) + datetime.timedelta(days=1)
        out.append(d.strftime(FMT))
    return out


def emit(out):
    cases, order = load_cases()
    for cid in order:
        c = cases[cid]
        out.write(json.dumps({"id": cid, "rrule": c["rrule"],
                              "dtstart": c["dtstart"], "limit": c["limit"]},
                             sort_keys=True) + "\n")


def read_out(path):
    d = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                o = json.loads(line)
                d[o["id"]] = o
    return d


def answer_of(row):
    """The occurrence list an adapter returned, or None for a refusal."""
    if row is None or "occurrences" not in row or row.get("error"):
        return None
    return row["occurrences"]


def classify(answer, case):
    """One of R, F, X, ERR. None is ERR and never matches anything."""
    if answer is None:
        return "ERR"
    if answer == case["rfc"]:
        return "R"
    if answer == case["floating"]:
        return "F"
    return "X"


def controls(cases, order):
    """(ok, lines). Both controls, always run, always reported."""
    lines, ok = [], True
    pos_bad = [cid for cid in order
               if classify(cases[cid]["floating"], cases[cid])
               != ("F" if cases[cid]["tz_dependent"] else "R")]
    lines.append("control POSITIVE: naive vs the RFC's printed lists -- "
                 "%d/%d as expected%s"
                 % (len(order) - len(pos_bad), len(order),
                    "" if not pos_bad else "  MISMATCH %s" % pos_bad))
    ok = ok and not pos_bad
    neg_bad = [cid for cid in order
               if classify(shift_a_day(cases[cid]["rfc"]), cases[cid]) != "X"]
    lines.append("control NEGATIVE: the same lists shifted one day -- "
                 "%d/%d correctly a third answer%s"
                 % (len(order) - len(neg_bad), len(order),
                    "" if not neg_bad else "  LEAKED %s" % neg_bad))
    ok = ok and not neg_bad
    nil_bad = [cid for cid in order if classify(None, cases[cid]) != "ERR"]
    lines.append("control NIL: a refusal is never agreement -- %d/%d"
                 % (len(order) - len(nil_bad), len(order)))
    ok = ok and not nil_bad
    # Not a pass/fail control, but it must be stated wherever the table is:
    # the timezone hazard and the 3.3.10 prohibition are the same eight rules.
    tzd = [cid for cid in order if cases[cid]["tz_dependent"]]
    pro = [cid for cid in order if cases[cid]["prohibited"]]
    lines.append("scope: %d of %d rules prohibited by 3.3.10 (UTC UNTIL under a "
                 "floating DTSTART), %d scorable; every tz-dependent rule (%d) "
                 "is among the prohibited ones: %s"
                 % (len(pro), len(order), len(order) - len(pro), len(tzd),
                    set(tzd) <= set(pro)))
    ok = ok and set(tzd) <= set(pro)
    return ok, lines


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--emit", action="store_true",
                    help="write the 42 cases as protocol NDJSON on stdout")
    ap.add_argument("--classify", nargs="*", metavar="OUT",
                    help="adapter output files, named out.<name>.ndjson")
    ap.add_argument("--json", metavar="PATH", help="write the table as JSON")
    a = ap.parse_args(argv)

    if a.emit:
        emit(sys.stdout)
        return 0
    if a.classify is None:
        ap.print_help()
        return 2

    cases, order = load_cases()
    ok, lines = controls(cases, order)
    for line in lines:
        print(line)
    print()
    if not ok:
        print("CONTROLS FAILED -- no row below may be cited.")
        return 1

    names, answers = [], {}
    for path in sorted(a.classify):
        name = os.path.basename(path)
        for pre, suf in (("out.", ".ndjson"),):
            if name.startswith(pre):
                name = name[len(pre):]
            if name.endswith(suf):
                name = name[:-len(suf)]
        names.append(name)
        answers[name] = read_out(path)

    grid = {}
    for cid in order:
        grid[cid] = {n: classify(answer_of(answers[n].get(cid)), cases[cid])
                     for n in names}

    scorable = [cid for cid in order if not cases[cid]["prohibited"]]
    w = max([len(n) for n in names] + [4])
    print("%-12s %-3s %-10s %s" % ("id", "ex", "scope", "  ".join(
        n.rjust(w) for n in names)))
    for cid in order:
        c = cases[cid]
        scope = "PROHIB" if c["prohibited"] else "-"
        if c["tz_dependent"]:
            scope += "/TZ"
        print("%-12s %-3d %-10s %s" % (
            cid, c["example"], scope,
            "  ".join(grid[cid][n].rjust(w) for n in names)))
    print()
    print("scored over the %d rules 3.3.10 permits here; the other %d are "
          "listed but charged to nobody." % (len(scorable), len(order) - len(scorable)))
    summary = {}
    for n in names:
        counts = {}
        for cid in scorable:
            counts[grid[cid][n]] = counts.get(grid[cid][n], 0) + 1
        summary[n] = counts
        print("%-*s  R=%-3d F=%-3d X=%-3d ERR=%-3d  of %d"
              % (w, n, counts.get("R", 0), counts.get("F", 0),
                 counts.get("X", 0), counts.get("ERR", 0), len(scorable)))

    if a.json:
        with open(a.json, "w") as f:
            json.dump({
                "source": "RFC 5545 3.8.5.3, corpus/rfc5545-examples.json",
                "cases": len(order),
                "tz_dependent": [cid for cid in order
                                 if cases[cid]["tz_dependent"]],
                "prohibited": [cid for cid in order if cases[cid]["prohibited"]],
                "scored": [cid for cid in order if not cases[cid]["prohibited"]],
                "controls": lines,
                "builds": names,
                "grid": {cid: grid[cid] for cid in order},
                "summary": summary,
                "detail": {cid: {k: cases[cid][k] for k in
                                 ("example", "desc", "rrule", "dtstart",
                                  "tzid", "limit", "expect_bound", "rfc",
                                  "floating", "tz_dependent", "prohibited")}
                           for cid in order},
            }, f, indent=1, sort_keys=True)
        print("\nwrote %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())

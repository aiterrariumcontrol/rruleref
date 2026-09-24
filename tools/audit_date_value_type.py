"""Run `corpus/date-value-type.json` against implementations, or classify.

`corpus/date-value-type.json` holds 18 cases whose `DTSTART` is a **DATE**,
not a `DATE-TIME`. Until this audit not one of them had been shown to an
implementation on `conformance/RESULTS.md`, and the reason was structural
rather than an oversight: `conformance/PROTOCOL.md`'s input line carries
`dtstart` as `YYYYMMDDTHHMMSS` and has **no field for a value type**. There is
no way to pose "this start is a date" over the wire, so `build_cases.py` never
selected them and no adapter ever saw one.

Standing rule 87 says an exclusion rule states a hazard and the hazard must be
*measured*, not argued. Measured, this one removes far less than it looks like:

* **12 of the 18 rules contain no reference to a value type at all** --
  `FREQ=DAILY`, `FREQ=MONTHLY;BYDAY=-1FR`, and so on. RRULE expansion is
  calendar arithmetic over the date fields; for these the DATE answer is
  exactly the DATE-TIME answer at `00:00:00` projected onto dates. They are
  ordinary conformance cases posed at midnight and nothing excludes them.
* **6 carry `BYSECOND`, `BYMINUTE` or `BYHOUR`**, which RFC 5545 3.3.10 says
  MUST be ignored under a DATE-valued `DTSTART`. The RFC's own remedy is a
  *reduction*: delete those parts. The reduced rule is one of the 12-style
  plain cases, so the board answers the DATE question for these too. What
  cannot be posed is the ignoring itself -- and see the warning below.
* **2 carry a DATE-valued `UNTIL`** (`UNTIL=20260108`). 3.3.10 requires
  `UNTIL` to have the same value type as `DTSTART`, so posed against the
  DATE-TIME `DTSTART` this protocol can express, those two are **prohibited
  rules** and an implementation's behaviour on them is not a conformance fact.
  This is the same shape as the eight `UNTIL=...Z` rules in finding 082,
  running the other way.

So two tables, and the second one inverts.

    python3 tools/audit_date_value_type.py --emit > dvt_cases.ndjson
    TZ=UTC <adapter> < dvt_cases.ndjson > out.<name>.ndjson    # PROTOCOL.md
    python3 tools/audit_date_value_type.py --classify out.*.ndjson

**Table REDUCED** asks each build for the RFC's reduced rule at `00:00:00` and
classifies against the corpus's DATE answer lifted to midnight. This is the
DATE question in the only form the wire can carry, and `D` is the right answer.

**Table WRITTEN** asks the 6 reducible rules *as written*. Here `D` is not a
virtue and `L` is not a defect, because the adapter was handed a DATE-TIME and
3.3.10's MUST-ignore does not apply to a DATE-TIME start: the correct answer
for the input actually given is `L`, the literal reading. A build answering `D`
would be dropping `BYHOUR` from a rule where it governs. This table therefore
measures nothing about 3.3.10 compliance; it measures whether the exclusion is
real, and confirms it is.

Codes:

    D    equals the corpus's DATE answer, lifted to 00:00:00
    L    equals the literal DATE-TIME reading, where that differs from D
    X    a third answer         ERR  the adapter refused the rule or crashed

Three controls run on every `--classify`, and all must be clean before any row
below may be cited:

  * POSITIVE -- `naive.expand` on the reduced rule reproduces the corpus's
    DATE answer on all 18. This pins the instrument and the reduction claim at
    once.
  * NEGATIVE -- the same lists shifted one day later are matched by nothing.
  * NIL -- a refusal is never agreement. None never equals None; the first
    version of finding 081's analysis compared `None` to `None` and reported
    six false reproductions.
"""
import argparse, datetime, hashlib, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
import naive  # noqa: E402

FMT = "%Y%m%dT%H%M%S"


def case_id(rrule, dtstart):
    return hashlib.sha256(
        ("dvt\n%s\n%s" % (rrule, dtstart)).encode()).hexdigest()[:12]


def expand_naive(rrule, dtstart, limit):
    ds = datetime.datetime.strptime(dtstart, FMT)
    return [x.strftime(FMT) for x in naive.expand(rrule, ds, limit=limit)][:limit]


def load_cases():
    """The 18 DATE-DTSTART cases as protocol cases, each in one or two forms.

    A case whose rule is already its own reduction is emitted once, as
    `form="reduced"`. A case with parts 3.3.10 says to ignore is emitted
    twice: once reduced and once as written.
    """
    path = os.path.join(REPO, "corpus", "date-value-type.json")
    with open(path) as f:
        doc = json.load(f)
    cases, order = {}, []
    for n, c in enumerate(doc["cases"]):
        dt = c["dtstart"] + "T000000"
        # The corpus's DATE answer, lifted into the protocol's DATE-TIME form.
        date_answer = [d + "T000000" for d in c["expect"]]
        # 3.3.10: UNTIL must match DTSTART's value type. The DTSTART this
        # protocol can pose is a DATE-TIME, so a DATE UNTIL is prohibited.
        prohibited = _has_date_until(c["rrule"])
        forms = [("reduced", c["reduced_rrule"])]
        if c["rrule"] != c["reduced_rrule"]:
            forms.append(("written", c["rrule"]))
        for form, rule in forms:
            cid = case_id(rule, dt)
            limit = len(c["expect"]) + (0 if _is_prefix(c) else 1)
            if cid in cases:
                # Four of the six reducible rules reduce to `FREQ=DAILY`,
                # which is also case 6 as written: distinct corpus cases,
                # one protocol case. Merge them, and require that they agree
                # about the answer -- a disagreement here would be a defect in
                # the corpus, not in any implementation.
                prev = cases[cid]
                if (prev["date_answer"] != date_answer
                        or prev["limit"] != limit or prev["form"] != form):
                    raise SystemExit(
                        "case_id %s: cases %s and %d share a rule and "
                        "disagree about the answer" % (cid, prev["cases"], n))
                prev["cases"].append(n)
                prev["prohibited"] = prev["prohibited"] or prohibited
                for part in c.get("ignored_parts") or []:
                    if part not in prev["ignored_parts"]:
                        prev["ignored_parts"].append(part)
                continue
            cases[cid] = {
                "cases": [n], "form": form, "rrule": rule, "dtstart": dt,
                "limit": limit, "date_answer": date_answer,
                "ignored_parts": list(c.get("ignored_parts") or []),
                "prohibited": prohibited, "why": c.get("why", ""),
            }
            order.append(cid)
    for cid in order:
        c = cases[cid]
        c["literal"] = expand_naive(c["rrule"], c["dtstart"], c["limit"])
        c["reduction_visible"] = c["literal"] != c["date_answer"]
    return cases, order


def _has_date_until(rrule):
    for part in rrule.split(";"):
        k, _, v = part.partition("=")
        if k.upper() == "UNTIL" and "T" not in v.upper():
            return True
    return False


def _is_prefix(c):
    """COUNT and UNTIL end the set inside the window; the rest are prefixes."""
    up = c["rrule"].upper()
    return not ("COUNT=" in up or "UNTIL=" in up)


def shift_a_day(occs):
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
    if row is None or "occurrences" not in row or row.get("error"):
        return None
    return row["occurrences"]


def classify(answer, case):
    """One of D, L, X, ERR. None is ERR and never matches anything."""
    if answer is None:
        return "ERR"
    if answer == case["date_answer"]:
        return "D"
    if answer == case["literal"]:
        return "L"
    return "X"


def controls(cases, order):
    lines, ok = [], True
    red = [cid for cid in order if cases[cid]["form"] == "reduced"]
    pos_bad = [cid for cid in red if classify(cases[cid]["literal"], cases[cid]) != "D"]
    lines.append("control POSITIVE: naive on the reduced rule vs the corpus's "
                 "DATE answer -- %d/%d reproduced%s"
                 % (len(red) - len(pos_bad), len(red),
                    "" if not pos_bad else "  MISMATCH %s" % pos_bad))
    ok = ok and not pos_bad
    neg_bad = [cid for cid in order
               if classify(shift_a_day(cases[cid]["date_answer"]), cases[cid]) != "X"]
    lines.append("control NEGATIVE: the same lists shifted one day -- "
                 "%d/%d correctly a third answer%s"
                 % (len(order) - len(neg_bad), len(order),
                    "" if not neg_bad else "  LEAKED %s" % neg_bad))
    ok = ok and not neg_bad
    nil_bad = [cid for cid in order if classify(None, cases[cid]) != "ERR"]
    lines.append("control NIL: a refusal is never agreement -- %d/%d"
                 % (len(order) - len(nil_bad), len(order)))
    ok = ok and not nil_bad
    # Scope, stated wherever the table is.
    pro = [cid for cid in red if cases[cid]["prohibited"]]
    wri = [cid for cid in order if cases[cid]["form"] == "written"]
    lines.append("scope: %d cases, %d reduced-form (%d prohibited by 3.3.10, "
                 "a DATE UNTIL under the DATE-TIME DTSTART this protocol can "
                 "pose; %d scorable) and %d written-form where 3.3.10's "
                 "MUST-ignore applies only to the DATE start the wire cannot "
                 "carry" % (len(red), len(red), len(pro), len(red) - len(pro),
                            len(wri)))
    # Every written form must actually differ from its reduction, or the
    # second table is measuring nothing.
    flat = [cid for cid in wri if not cases[cid]["reduction_visible"]]
    lines.append("control SPLIT: every written form differs from the DATE "
                 "answer -- %d/%d%s" % (len(wri) - len(flat), len(wri),
                                        "" if not flat else "  FLAT %s" % flat))
    ok = ok and not flat
    return ok, lines


def _table(title, cids, cases, names, grid, note):
    w = max([len(n) for n in names] + [4])
    print(title)
    print("%-12s %-4s %-8s %-46s %s" % ("id", "case", "scope", "rrule",
                                        "  ".join(n.rjust(w) for n in names)))
    for cid in cids:
        c = cases[cid]
        print("%-12s %-4s %-8s %-46s %s" % (
            cid, ",".join(str(i) for i in c["cases"]),
            "PROHIB" if c["prohibited"] else "-",
            c["rrule"][:46],
            "  ".join(grid[cid][n].rjust(w) for n in names)))
    scorable = [cid for cid in cids if not cases[cid]["prohibited"]]
    print()
    print(note % len(scorable))
    summary = {}
    for n in names:
        counts = {}
        for cid in scorable:
            counts[grid[cid][n]] = counts.get(grid[cid][n], 0) + 1
        summary[n] = counts
        print("%-*s  D=%-3d L=%-3d X=%-3d ERR=%-3d  of %d"
              % (w, n, counts.get("D", 0), counts.get("L", 0),
                 counts.get("X", 0), counts.get("ERR", 0), len(scorable)))
    print()
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--emit", action="store_true",
                    help="write the cases as protocol NDJSON on stdout")
    ap.add_argument("--classify", nargs="*", metavar="OUT",
                    help="adapter output files, named out.<name>.ndjson")
    ap.add_argument("--json", metavar="PATH", help="write the tables as JSON")
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
        if name.startswith("out."):
            name = name[4:]
        if name.endswith(".ndjson"):
            name = name[:-7]
        names.append(name)
        answers[name] = read_out(path)

    grid = {cid: {n: classify(answer_of(answers[n].get(cid)), cases[cid])
                  for n in names} for cid in order}

    red = [cid for cid in order if cases[cid]["form"] == "reduced"]
    wri = [cid for cid in order if cases[cid]["form"] == "written"]
    s_red = _table(
        "TABLE REDUCED -- the DATE answer, asked in the only form the wire "
        "carries.\nD is the right answer here.",
        red, cases, names, grid,
        "scored over the %d rules 3.3.10 permits here; the prohibited ones "
        "are listed and charged to nobody.")
    s_wri = _table(
        "TABLE WRITTEN -- the same 6 rules as written, at a DATE-TIME start.\n"
        "L is the RIGHT answer here and D would be a defect: 3.3.10's "
        "MUST-ignore\nis conditioned on a DATE start, which this protocol "
        "cannot express.",
        wri, cases, names, grid,
        "scored over %d rules; read the header before reading the counts.")

    if a.json:
        with open(a.json, "w") as f:
            json.dump({
                "source": "corpus/date-value-type.json",
                "controls": lines, "builds": names,
                "reduced": red, "written": wri,
                "prohibited": [c for c in order if cases[c]["prohibited"]],
                "grid": grid,
                "summary_reduced": s_red, "summary_written": s_wri,
                "detail": {cid: {k: cases[cid][k] for k in
                                 ("cases", "form", "rrule", "dtstart", "limit",
                                  "date_answer", "literal", "prohibited",
                                  "ignored_parts", "reduction_visible")}
                           for cid in order},
            }, f, indent=1, sort_keys=True)
        print("wrote %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""The conformance harness: the case selection, the expect_bound classifier,
and an end-to-end score.

The point of this file is that the *published* number in conformance/RESULTS.md
cannot drift silently. It pins:

1. `expect_bound == "complete"` really means complete. Each such case is
   re-expanded with an unbounded dateutil and must end exactly where `expect`
   ends. This is the check that caught the classifier's first version, which
   called three FREQ=SECONDLY-with-UNTIL cases complete when the occurrence cap
   had bitten first.
2. Nothing in cases.ndjson is invalid, unsynchronized, or vacuous.
3. Case ids are stable and collision-free.
4. The dateutil adapter scores every case. It must: dateutil corroborated them
   all. A failure here is a harness defect, not a dateutil defect.
5. invariants.py's transcription of the sec. 3.3.10 table and its `survives`
   rule, and the fact that dateutil violates nothing it checks. The first
   version of that module checked every part unconditionally and would have
   published 31 false claims against ical4j (finding 016).
"""
import sys, os, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "conformance"))
import env
env.add_dateutil_to_path()
from datetime import datetime
from dateutil.rrule import rrulestr
import build_cases
import build_corpus

FMT = "%Y%m%dT%H%M%S"
FAILURES = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (("  " + extra) if extra else ""))
    if not cond:
        FAILURES.append(name)


def unbounded(rule, ds, cap):
    """dateutil's own expansion, stopped only by `cap` -- not by any horizon."""
    out = []
    for x in rrulestr("RRULE:" + rule, dtstart=ds):
        out.append(x.strftime(FMT))
        if len(out) >= cap:
            break
    return out


def _check_invariants():
    """invariants.py against RFC 5545 lines 2418 and 2431-2459, and dateutil."""
    import invariants as I
    tab = [("BYMONTH", "WEEKLY", {}, "Limit"),
           ("BYMONTH", "YEARLY", {}, "Expand"),
           ("BYWEEKNO", "DAILY", {}, None),
           ("BYYEARDAY", "WEEKLY", {}, None),
           ("BYMONTHDAY", "WEEKLY", {}, None),
           ("BYMONTHDAY", "MONTHLY", {}, "Expand"),
           ("BYDAY", "WEEKLY", {}, "Expand"),
           ("BYDAY", "MONTHLY", {"BYMONTHDAY"}, "Limit"),      # Note 1
           ("BYDAY", "MONTHLY", {}, "Expand"),
           ("BYDAY", "YEARLY", {"BYYEARDAY"}, "Limit"),        # Note 2
           ("BYDAY", "YEARLY", {}, "Expand"),
           ("BYHOUR", "DAILY", {}, "Expand"),
           ("BYHOUR", "HOURLY", {}, "Limit")]
    bad = [(p, f, got) for p, f, pr, want in tab
           if (got := I.classify(p, f, pr)) != want]
    check("invariants.py transcribes the 3.3.10 table", not bad, str(bad))
    # A later Expand on the same component destroys the guarantee; a later
    # Limit, or an Expand on another component, does not.
    surv = [(not I.survives("BYMONTH", "WEEKLY", {"BYDAY", "BYMONTH"})),
            I.survives("BYMONTH", "WEEKLY", {"BYMONTH"}),
            I.survives("BYMONTH", "DAILY", {"BYMONTH", "BYHOUR"}),
            I.survives("BYDAY", "YEARLY", {"BYWEEKNO", "BYDAY"}),
            not I.survives("BYYEARDAY", "YEARLY", {"BYYEARDAY", "BYMONTHDAY"})]
    check("invariants.py's survives() follows the application order", all(surv))
    v = list(I.violations("FREQ=WEEKLY;BYDAY=MO;BYMONTH=7", ["20270628T090000"]))
    check("a known order-dependent mismatch is not reported as guaranteed",
          v and not v[0][3], str(v))
    v = list(I.violations("FREQ=YEARLY;BYWEEKNO=53;BYDAY=WE", ["20290102T090000"]))
    check("a BYDAY weekday mismatch is reported as guaranteed",
          v and v[0][3] and v[0][1] == "BYDAY", str(v))


def main():
    corpus = json.load(open(os.path.join(ROOT, "corpus", "corroborated.json")))["cases"]

    # 1. The classifier agrees with the committed corpus, and "complete" is true.
    reclassified = 0
    for c in corpus:
        ds = datetime.strptime(c["dtstart"], FMT)
        occ = [datetime.strptime(x, FMT) for x in c["expect"]]
        if build_corpus.expect_bound(c["rrule"], ds, occ) != c["expect_bound"]:
            reclassified += 1
    check("expect_bound in the corpus matches the classifier",
          reclassified == 0, "%d disagree" % reclassified)

    wrong = []
    complete = [c for c in corpus if c["expect_bound"] == "complete"]
    for c in complete:
        got = unbounded(c["rrule"], datetime.strptime(c["dtstart"], FMT),
                        len(c["expect"]) + 1)
        if got != c["expect"]:
            wrong.append(c["rrule"])
    check("every 'complete' case really ends where expect ends",
          not wrong, "%d/%d wrong: %s" % (len(wrong), len(complete), wrong[:3]))

    # 2/3. The published subset.
    rows = list(build_cases.select(corpus))
    ids0 = [r["id"] for r in rows]
    check("cases.ndjson is non-empty", len(rows) > 1000, "%d" % len(rows))
    by_id = {}
    for c in corpus:
        by_id[build_cases.case_id(c["rrule"], c["dtstart"])] = c
    unfit = [r["id"] for r in rows
             if not (by_id[r["id"]]["rule_valid"]
                     and by_id[r["id"]]["dtstart_synchronized"])]
    check("every selected case is valid and synchronized", not unfit, str(unfit[:3]))
    dropped = [c for c in corpus
               if c["rule_valid"] and c["dtstart_synchronized"]
               and build_cases.case_id(c["rrule"], c["dtstart"]) not in set(ids0)]
    check("every selected case's UNTIL matches DTSTART's value type",
          not [r for r in rows
               if build_cases.until_type_mismatch(r["rrule"], r["dtstart"])])
    check("the only cases dropped are vacuous or UNTIL-type mismatches",
          all((c["expect_bound"] == "horizon" and not c["expect"])
              or build_cases.until_type_mismatch(c["rrule"], c["dtstart"])
              for c in dropped),
          "%d dropped" % len(dropped))
    bad = [r for r in rows if r["expect_bound"] == "horizon" and not r["expect"]]
    check("no vacuous case (empty expect at the horizon)", not bad, str(len(bad)))
    ids = [r["id"] for r in rows]
    check("case ids are unique", len(set(ids)) == len(ids))
    check("case id is a pure function of rule and dtstart",
          build_cases.case_id("FREQ=DAILY", "20260302T090000") ==
          build_cases.case_id("FREQ=DAILY", "20260302T090000"))
    for r in rows:
        want = len(r["expect"]) + (1 if r["expect_bound"] == "complete" else 0)
        if r["limit"] != want:
            check("limit is derived from expect_bound", False, r["id"])
            break
    else:
        check("limit is derived from expect_bound", True)

    committed = os.path.join(ROOT, "conformance", "cases.ndjson")
    if os.path.exists(committed):
        on_disk = [json.loads(l) for l in open(committed) if l.strip()]
        check("committed cases.ndjson is what build_cases.py produces",
              on_disk == rows, "%d on disk vs %d generated" % (len(on_disk), len(rows)))
    else:
        check("committed cases.ndjson exists", False)

    # 4. End to end.
    score = os.path.join(ROOT, "conformance", "score.py")
    adapter = os.path.join(ROOT, "conformance", "adapters", "dateutil_adapter.py")
    p = subprocess.run([sys.executable, score, "--", sys.executable, adapter],
                       capture_output=True, text=True)
    _check_invariants()
    check("dateutil adapter passes every case", p.returncode == 0,
          p.stdout.strip().replace("\n", " | ")[:300])

    print("\n%d checks failed" % len(FAILURES) if FAILURES else "\nall checks passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())

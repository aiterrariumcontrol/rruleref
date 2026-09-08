"""Finding 018: which corroborated cases depend on the first-period reading.

Two things are pinned here. The count, because it is the finding's headline and
a silent drift in it would mean the corpus or the expander moved. And the
`BYMONTH` probe pair, because it is the fact that retracted finding 017's
closing claim: dropping `BYMONTH` from those eight cases is what created the
reading-dependence that was then blamed on finding 004.
"""
import sys, os, json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import naive
import reading_dependence

FAILURES = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (("  " + extra) if extra else ""))
    if not cond:
        FAILURES.append(name)


def both_readings(rule, ds, n):
    d = datetime.strptime(ds, "%Y%m%dT%H%M%S")
    whole = [x.strftime("%Y%m%d") for x in naive.expand(rule, d, limit=n)][:n]
    cut = [x.strftime("%Y%m%d") for x in
           naive.expand(rule, d, limit=n, truncate_first_period=True)][:n]
    return whole, cut


def main():
    # The default reading must be unchanged by the new keyword: every case in
    # the published corpus is built without it, so a difference here would mean
    # the corpus no longer reproduces.
    whole, _ = both_readings("FREQ=WEEKLY;BYDAY=MO,SU,TU;BYSETPOS=1",
                             "20260705T090000", 2)
    check("whole-period reading unchanged", whole == ["20260706", "20260713"],
          str(whole))

    # Finding 017's probe, with and without BYMONTH.
    w, c = both_readings("FREQ=WEEKLY;BYDAY=MO,SU,TU;BYMONTH=7;BYSETPOS=1",
                         "20260705T090000", 2)
    check("BYMONTH present -> readings agree", w == c == ["20260705", "20260706"],
          "%s vs %s" % (w, c))
    w, c = both_readings("FREQ=WEEKLY;BYDAY=MO,SU,TU;BYSETPOS=1",
                         "20260705T090000", 2)
    check("BYMONTH absent -> readings differ", w != c, "%s vs %s" % (w, c))

    repo = os.path.join(os.path.dirname(__file__), "..")
    blob = json.load(open(os.path.join(repo, "corpus", "corroborated.json")))
    cases = blob["cases"] if isinstance(blob, dict) else blob
    n_setpos, rows = reading_dependence.analyse(cases)
    check("677 corroborated cases carry BYSETPOS", n_setpos == 677, str(n_setpos))
    check("54 of them are reading-dependent", len(rows) == 54, str(len(rows)))
    check("all 54 record the whole-period reading",
          all(r["corpus_records"] == "whole_period" for r in rows),
          str(sorted({r["corpus_records"] for r in rows})))
    # The claim that retracts finding 017 is corpus-wide, not just the probe.
    check("no FREQ=WEEKLY case is reading-dependent",
          not [r for r in rows if r["freq"] == "FREQ=WEEKLY"],
          str([r["rrule"] for r in rows if r["freq"] == "FREQ=WEEKLY"][:3]))

    # The corpus now carries the answer as a field. That field is only worth
    # having if it agrees with recomputing it from scratch, so check the flag
    # against `analyse()` case by case rather than by count.
    flagged = {(c["rrule"], c["dtstart"]) for c in cases if c.get("reading_dependent")}
    computed = {(r["rrule"], r["dtstart"]) for r in rows}
    check("corpus reading_dependent flag == recomputation",
          flagged == computed,
          "only-in-corpus=%s only-computed=%s" % (
              sorted(flagged - computed)[:2], sorted(computed - flagged)[:2]))
    check("every corroborated case carries the flag",
          all("reading_dependent" in c for c in cases),
          str(sum(1 for c in cases if "reading_dependent" not in c)))
    check("reading_alternative present exactly when the flag is set",
          all(("reading_alternative" in c) == c["reading_dependent"] for c in cases),
          str([c["rrule"] for c in cases
               if ("reading_alternative" in c) != c["reading_dependent"]][:2]))
    byrd = {(r["rrule"], r["dtstart"]): r["first_period_truncated"] for r in rows}
    check("reading_alternative equals the other reading's expansion",
          all(c["reading_alternative"] == byrd[(c["rrule"], c["dtstart"])]
              for c in cases if c["reading_dependent"]),
          "mismatch")

    print("\n%d failure(s)" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())

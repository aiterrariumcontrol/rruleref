"""Finding 022 as a debugger diagnostic, checked against a second implementation.

`web/src/diagnostics.js` now shows, beside the user's own expansion, what the
*seed-limit* reading of RFC 5545 3.3.10 would give for `FREQ=WEEKLY` with
`BYMONTH`. It computes that reading by a trick -- delete `BYMONTH`, expand, then
keep only the occurrences whose week's seed falls in a named month -- rather
than by a second expander. A trick that is wrong would be invisible in the UI:
the user would simply be shown a false alternative.

So it is checked here against `findings/repro/022-seed-limit-reading.py`, which
implements the reading directly, week by week, and which produced the tables in
finding 022. The two share no code. Both readings are compared, not just the
new one, because a JS/Python disagreement about the *default* reading would
otherwise be blamed on the seed-limit code.

Also pinned: the diagnostic must stay silent where the two readings coincide.
A note that always fires tells a user nothing.

Skips, loudly, when node is not installed.
"""
import importlib.util
import json
import os
import shutil
import subprocess
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

fails = []

_spec = importlib.util.spec_from_file_location(
    "ref022", os.path.join(ROOT, "findings", "repro", "022-seed-limit-reading.py"))
ref022 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ref022)

# The four probe rules of finding 022, plus the one where the readings coincide
# (the finding's "one case the reading question cannot reach at all") and a
# plain weekly rule with no BYMONTH boundary to straddle.
CASES = [
    ("P1", "FREQ=WEEKLY;BYDAY=MO,SU,TU;BYMONTH=7", "20260705T090000", 15, True),
    ("P3", "FREQ=WEEKLY;BYDAY=MO,SU,TU;BYMONTH=7;BYSETPOS=1", "20260705T090000", 8, True),
    ("Q1", "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYMONTH=7;BYSETPOS=1",
     "20260701T090000", 6, True),
    ("Q4", "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYMONTH=9,10,11,12;BYSETPOS=1",
     "20260901T090000", 10, True),
    ("coincide", "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYMONTH=7;BYSETPOS=-1",
     "20260703T090000", 6, False),
    ("whole-year", "FREQ=WEEKLY;BYDAY=MO,WE;BYMONTH=1,2,3,4,5,6,7,8,9,10,11,12",
     "20260105T090000", 12, False),
    # INTERVAL>1. This case does *not* discriminate a wrong stride: the
    # occurrences already come from an INTERVAL-respecting expansion, so the
    # stride cancels between the division and the multiplication that recover
    # the seed. It is here because the reading still has to be right for
    # fortnightly rules, and because that cancellation was checked rather
    # than assumed -- replacing 7*INTERVAL with 7 leaves every row unchanged.
    ("interval2", "FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,SU,TU;BYMONTH=7",
     "20260705T090000", 12, True),
]


def run_js():
    lines = "".join(
        json.dumps({"id": name, "rrule": rule, "dtstart": ds, "limit": n}) + "\n"
        for name, rule, ds, n, _ in CASES)
    r = subprocess.run(["node", os.path.join(ROOT, "web", "test", "seed-limit-weekly.mjs")],
                       input=lines, capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        fails.append("the node harness exited %d: %s" % (r.returncode, r.stderr.strip()[-800:]))
        return {}
    return {json.loads(l)["id"]: json.loads(l) for l in r.stdout.splitlines() if l.strip()}


def test_seed_limit_matches_the_reference_implementation():
    got = run_js()
    for name, rule, ds, n, expect_note in CASES:
        row = got.get(name)
        if row is None:
            fails.append("%s: the harness produced no row" % name)
            continue
        dt = datetime.strptime(ds, "%Y%m%dT%H%M%S")
        want_filter = ref022.expand(rule, dt, n, "filter-instances")
        want_seed = ref022.expand(rule, dt, n, "seed-limit")

        if row["occurrences"] != want_filter:
            fails.append("%s: the expander disagrees with the reference on the "
                         "default reading\n    js  %s\n    py  %s"
                         % (name, " ".join(row["occurrences"]), " ".join(want_filter)))
        else:
            print("PASS %-11s default reading agrees (%d dates)" % (name, n))

        if expect_note:
            if row["seedLimit"] is None:
                fails.append("%s: the readings differ but no diagnostic fired" % name)
            elif row["seedLimit"] != want_seed:
                fails.append("%s: the diagnostic's seed-limit list is not the "
                             "reference's\n    js  %s\n    py  %s"
                             % (name, " ".join(row["seedLimit"]), " ".join(want_seed)))
            else:
                print("PASS %-11s seed-limit list matches the reference" % name)
        else:
            if want_filter != want_seed:
                fails.append("%s: the test's own premise is wrong -- the reference "
                             "says these readings differ" % name)
            elif row["seedLimit"] is not None:
                fails.append("%s: the readings coincide, yet the diagnostic fired "
                             "and showed %s" % (name, " ".join(row["seedLimit"])))
            else:
                print("PASS %-11s readings coincide and the diagnostic is silent" % name)


def test_dtstart_loss_is_reported_exactly_when_it_happens():
    got = run_js()
    for name, rule, ds, n, expect_note in CASES:
        row = got.get(name)
        if row is None or row["seedLimit"] is None:
            continue
        lost = row["occurrences"][0] != row["seedLimit"][0] and \
            row["occurrences"][0] == datetime.strptime(ds, "%Y%m%dT%H%M%S").strftime("%Y%m%d")
        if bool(row["dropsDtstart"]) != lost:
            fails.append("%s: DTSTART loss is %s but the note %s say so"
                         % (name, "real" if lost else "not real",
                            "does" if row["dropsDtstart"] else "does not"))
        else:
            print("PASS %-11s DTSTART-loss sentence present iff DTSTART is lost" % name)


def main():
    if not shutil.which("node"):
        print("SKIP: node is not installed; the diagnostic cannot be run")
        return 0
    test_seed_limit_matches_the_reference_implementation()
    test_dtstart_loss_is_reported_exactly_when_it_happens()
    if fails:
        print("\n%d FAILED" % len(fails))
        for f in fails:
            print("  " + f)
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

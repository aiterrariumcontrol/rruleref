#!/usr/bin/env python3
"""Guards finding 124: the slow band's mechanism.

Fast. The finding's own repro takes about twenty minutes because it times
seventy-one cases against a Perl library; this holds the parts that can be
checked in seconds.

CHECK 4 TOUCHES `DateTime::Event::ICal` AND IS SKIPPED LOUDLY WITHOUT IT. That
is wake 187's lesson: a check whose subject is absent must say which check did
not run, not quietly pass. Checks 1-3 are artifact-only and run everywhere.

CHECK 3b EXISTS BECAUSE THE ABLATION ONCE COUNTED A CRASH AS A SPEEDUP. See the
correction in the finding: a removed rule part can change the FAILURE MODE and
not just the cost, and this library's failure mode is fast.

THE VACUITY GUARD IS CHECK 3. A predicate that called every rule expensive would
satisfy "all 71 slow cases are classified" and mean nothing at all. So the test
asserts the predicate also calls a large share of the corpus cheap. Finding 124's
whole claim is that it is necessary-side only, and a test that could not fail on
a constant-True predicate would not be testing that claim.

WAKE 191 ASKED THAT QUESTION OF THIS TEST'S OWN GUARDS AND TWO OF THEM FAILED IT.
Emptying `ablated_died` in the artifact, and emptying 122's `slow` list, each left
all six checks printing ok -- because "no dead ablation was counted as faster" and
"every timed-slow case has a mechanism" are both true of the empty set. CHECK 0
and CHECK 3c close those two holes, and each was watched to fail on exactly the
mutation it exists for.

CHECK 5 IS THE ONE THAT MATTERS, AND IT IS NOT AN ARTIFACT CHECK. No amount of
reading the stored data can notice that the harness stopped reading the adapter's
error field, because that regression writes a self-consistent artifact in which
nothing died. So check 5 injects a fast death into `run` and requires the row to
come back `died`; deleting the `err` branch of the classifying line makes it
report a FABRICATED SPEEDUP, and check 5 catches that. Check 5b is its control
arm: the same fast timing with no error must still be `faster`, or a classifier
that called everything dead would pass.
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "findings", "repro"))
import importlib
m = importlib.import_module("124-what-makes-dtical-slow")

CASES = os.path.join(REPO, "conformance", "cases.ndjson")
STORED = os.path.join(REPO, "findings", "data", "124-dtical-cost-classes.json")
ADAPTER = os.path.join(REPO, "conformance", "adapters", "perl",
                       "dtical_adapter.pl")
TIMES = os.path.join(REPO, "findings", "data", "122-dtical-case-times.json")

fails = []


def check(name, ok, detail=""):
    print("%-4s %s%s" % ("ok" if ok else "FAIL", name,
                         "" if ok else "  -- " + detail))
    if not ok:
        fails.append(name)


def have_dtical():
    try:
        p = subprocess.run(["perl", "-MDateTime::Event::ICal", "-e1"],
                           capture_output=True, timeout=60)
        return p.returncode == 0
    except Exception:
        return False


def main():
    cases = {}
    for line in open(CASES):
        c = json.loads(line)
        cases[c["id"]] = c
    stored = json.load(open(STORED))
    timed = {d["id"] for d in json.load(open(TIMES))["slow"]}

    # 0. LIVENESS OF THE POPULATION. Checks 1 and 2 are both statements about
    #    `timed`, and both are satisfied by the EMPTY SET -- so if 122's
    #    artifact ever lost its `slow` list, the test's whole subject would
    #    vanish and every check would still print ok. Watched to fail at wake
    #    191 by emptying that list. The floor is loose on purpose: a re-run of
    #    122 on another machine may legitimately move the count (it was 71),
    #    but it cannot legitimately drop it to a handful.
    check("0 the timed-slow population is not empty", len(timed) > 20,
          "only %d timed-slow cases -- checks 1 and 2 are now vacuous"
          % len(timed))

    # 1. The predicate still classifies every case finding 122 timed as slow.
    #    Recomputed from cases.ndjson, not read back from the artifact, so a
    #    corpus regeneration that changed a rule would break this.
    live = {cid: m.classify(cases[cid]["rrule"]) for cid in timed}
    cheap = sorted(c for c, v in live.items() if v == "cheap")
    check("1 every timed-slow case has a mechanism", not cheap,
          "unexplained: " + " ".join(cheap))

    # 2. The stored classification still matches the live one, case for case.
    drift = sorted(c for c in timed if stored["classes"].get(c) != live[c])
    check("2 stored classes match the live predicate", not drift,
          "drifted: " + " ".join(drift[:8]))

    # 3. VACUITY. The predicate must call plenty of the corpus cheap, or
    #    check 1 is satisfied by a constant and finding 124's necessary-side
    #    claim is untestable.
    allcls = {cid: m.classify(c["rrule"]) for cid, c in cases.items()}
    n_cheap = sum(1 for v in allcls.values() if v == "cheap")
    check("3 the predicate is not constant-True",
          n_cheap > len(cases) // 4,
          "only %d of %d cases called cheap" % (n_cheap, len(cases)))

    # 3b. A DEATH IS NOT A SPEEDUP. Wake 189: the ablation harness read the
    #     adapter's error field and never used it, so five of the 71 ablations
    #     were scored as having dropped below the 5s floor when what actually
    #     happened was a crash at Recurrence.pm:822 in about 0.1s. For this
    #     subject the characteristic failure is FAST, so a verdict written only
    #     in seconds cannot tell the two apart. The artifact must carry the
    #     died list, and no case may be both dead and counted as faster.
    died = stored.get("ablated_died")
    check("3b the artifact records which ablations died", died is not None,
          "no ablated_died key -- the instrument predates wake 189's fix and "
          "its below_floor verdicts cannot be trusted")
    if died is not None:
        below = stored.get("ablated_below_floor", {})
        both = sorted(c for c in died if below.get(c))
        check("3b a dead ablation is not also counted as faster", not both,
              "counted as speedups: " + " ".join(both))

    # 3c. THE SAME QUESTION ASKED OF 3b ITSELF. `died is not None` is true of
    #     the EMPTY LIST, and so is "no dead ablation is counted as faster" --
    #     so at wake 191 both 3b checks still printed ok after I emptied
    #     `ablated_died` in the artifact. The death list and the per-case
    #     outcome map are written from the same rows but are separate fields,
    #     so holding them to each other catches a list that stopped being
    #     populated while the outcomes still record deaths.
    outcome = stored.get("ablated_outcome") or {}
    check("3c the died list and the per-case outcomes agree",
          set(died or []) == {c for c, v in outcome.items() if v == "died"},
          "died=%r but outcomes say %r"
          % (sorted(died or []),
             sorted(c for c, v in outcome.items() if v == "died")))

    # 4. The mechanism itself, on the smallest cell of the grid that shows it.
    #    One rule, one part added, limit 3: BYSETPOS must cost multiples of the
    #    same rule without it. The margin is deliberately loose -- the finding's
    #    measured ratio on this cell is around twentyfold and the assertion is
    #    threefold, so machine load cannot turn a real effect into a failure.
    if not have_dtical():
        print("SKIP 4 the BYSETPOS cost ratio -- perl DateTime::Event::ICal is "
              "not installed here, so the one check with a live subject did "
              "NOT run")
    else:
        base = "FREQ=DAILY;BYMONTHDAY=5"
        t = {}
        for rrule in (base, base + ";BYSETPOS=-1"):
            el, n, err = m.run(rrule, "20260805T090000", 3, 60)
            t[rrule] = el
        ratio = t[base + ";BYSETPOS=-1"] / max(t[base], 1e-6)
        check("4 BYSETPOS costs multiples of the same rule without it",
              ratio > 3.0, "ratio only %.2f (%.2fs vs %.2fs)"
              % (ratio, t[base + ";BYSETPOS=-1"], t[base]))

    # 5. THE DETECTION PATH, NOT THE ARTIFACT. Checks 3b and 3c read what the
    #    harness wrote; neither can tell that the harness STOPPED READING the
    #    adapter's error field, which is exactly the wake-189 bug -- that
    #    regression writes an artifact whose outcomes and died list agree
    #    perfectly, both saying nothing died. The only thing that can fail on
    #    it is a test of the classifying line. So: inject a FAST DEATH into
    #    `run` and require the row to come back `died` and NOT below_floor.
    #    The control arm injects the same fast timing with NO error and
    #    requires `faster` -- without it this check would also pass on a
    #    classifier that called everything dead.
    case = next((c for c in cases.values()
                 if m.classify(c["rrule"]) == "bysetpos" and m.ablate(c["rrule"])),
                None)
    if case is None:
        check("5 a fast death is classified died, not faster", False,
              "no ablatable bysetpos case in the corpus to inject into")
    else:
        quiet = lambda *a, **k: None
        one = {case["id"]: case}
        real = m.run
        try:
            m.run = lambda *a, **k: (0.1, None, "Can't call method \"subtract\" "
                                     "at Recurrence.pm line 822")
            dead = m.ablation(one, {case["id"]: 9999.0}, quiet)
            m.run = lambda *a, **k: (0.1, 3, None)
            live = m.ablation(one, {case["id"]: 9999.0}, quiet)
        finally:
            m.run = real
        ok = (len(dead) == 1 and dead[0].get("outcome") == "died"
              and dead[0].get("below_floor") is False)
        check("5 an injected fast death is classified died, not below_floor",
              ok, "row came back %r" % (dead[0] if dead else None))
        ctrl = (len(live) == 1 and live[0].get("outcome") == "faster"
                and live[0].get("below_floor") is True)
        check("5b CONTROL: the same fast timing with no error is still faster",
              ctrl, "row came back %r" % (live[0] if live else None))

    print("\n%d check(s) failed" % len(fails) if fails else "\nall checks pass")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

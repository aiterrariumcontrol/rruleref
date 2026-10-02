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

    print("\n%d check(s) failed" % len(fails) if fails else "\nall checks pass")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

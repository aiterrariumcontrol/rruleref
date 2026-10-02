#!/usr/bin/env python3
"""The adapter-backed property bridge agrees with the in-process expander.

`src/adapter_expanders.py` reaches an implementation over the line protocol and
has to rebuild, out of per-line `limit` answers, the horizon-and-cap bounded
expansion that `src/properties.py` asks for. That reconstruction is the whole
risk in finding 118: get it wrong and the sweep either invents failures or,
worse, hides them, and nothing in the output would say so.

The `dateutil` adapter wraps the same library as `src/expanders.py`'s
`dateutil` expander, so the two paths must produce the *identical* property
result -- not a similar tally, the same failing (property, rule, dtstart)
triples. That is the check, run over a fixed sample so it stays a few seconds.

It also pins the two settled facts about the bridge that a later edit could
quietly break: that it reaches a fixpoint at all, and that a refusal arrives as
an ERROR rather than as a silent empty expansion.

Needs only Python and the vendored dateutil. About five seconds.
"""
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import properties as P
import adapter_expanders as A
from expanders import EXPANDERS
from run_properties import load_rules
from run_properties_adapters import sweep

SAMPLE = 80
SEED = 11
FAIL = []


def check(label, ok, detail=""):
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", label,
                           ("   -- " + detail) if detail else ""))
    if not ok:
        FAIL.append(label)


def in_process(rules):
    tally, keys = {}, set()
    exp = EXPANDERS["dateutil"]
    for rule, ds in rules:
        res = P.check(exp, rule, datetime.strptime(ds, P.FMT))
        for pid, r in res.items():
            t = tally.setdefault(pid, {})
            t[r["status"]] = t.get(r["status"], 0) + 1
            if r["status"] in (P.FAIL, P.ERROR):
                keys.add((pid, rule, ds))
    return tally, keys


def main():
    import random
    rules = load_rules()
    rules = random.Random(SEED).sample(rules, min(SAMPLE, len(rules)))
    print("%d rules, seed %d" % (len(rules), SEED))

    want_tally, want_keys = in_process(rules)
    exp = A.AdapterExpander("dateutil", cap=P.CAP)
    got_tally, got_failures, passes = sweep(exp, rules, P.HORIZON_DAYS, P.CAP,
                                            verbose=False)
    got_keys = {(x["property"], x["rrule"], x["dtstart"])
                for x in got_failures}

    check("bridge reached a fixpoint", passes >= 1, "%d passes" % passes)
    check("tally is identical", want_tally == got_tally,
          "" if want_tally == got_tally
          else "in-process %r vs adapter %r" % (want_tally, got_tally))
    check("the same failing triples", want_keys == got_keys,
          "%d vs %d" % (len(want_keys), len(got_keys)))
    check("every expansion came from the adapter, none from the placeholder",
          exp.misses == 0, "%d misses in the reported pass" % exp.misses)

    # A refusal must surface as ERROR. `UNTIL` with a `Z` on a floating
    # DTSTART is the refusal dateutil actually makes (PROTOCOL.md), so it is
    # the one probe here that does not depend on a defect staying unfixed.
    bad = A.AdapterExpander("dateutil", cap=8)
    res = P.check(bad, "FREQ=DAILY;UNTIL=20260401T000000Z",
                  datetime(2026, 3, 2, 9, 0, 0))
    bad.resolve()
    res = P.check(bad, "FREQ=DAILY;UNTIL=20260401T000000Z",
                  datetime(2026, 3, 2, 9, 0, 0))
    check("a refused rule lands in ERROR, not in an empty pass",
          res["P1"]["status"] == P.ERROR, res["P1"]["status"])

    print("FAILED: %s" % ", ".join(FAIL) if FAIL else "all checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

"""Run every property over every rule the corpus already vouches for.

Rules come from ``corpus/corroborated.json``, restricted to cases whose
DTSTART is synchronized with the rule. RFC 5545 3.8.5.3 declares the
recurrence set undefined otherwise, and a property violation inside undefined
territory says nothing about conformance -- that mistake produced a withdrawn
bug report on 2026-09-05.

Output: ``findings/data/properties.json``, one row per (expander, rule,
property), plus a summary. Failures are written out in full; passes are
counted.

    python3 src/run_properties.py [--sample N] [--out PATH]
"""
import argparse
import json
import os
import random
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.path.dirname(HERE)
import properties as P
from expanders import EXPANDERS


def load_rules(path=None):
    path = path or os.path.join(REPO, "corpus", "corroborated.json")
    cases = json.load(open(path))["cases"]
    seen, out = set(), []
    for c in cases:
        if not c.get("dtstart_synchronized"):
            continue
        key = (c["rrule"], c["dtstart"])
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--horizon-days", type=int, default=P.HORIZON_DAYS)
    ap.add_argument("--cap", type=int, default=P.CAP)
    ap.add_argument("--out", default=os.path.join(REPO, "findings", "data",
                                                  "properties.json"))
    a = ap.parse_args(argv)

    rules = load_rules()
    if a.sample:
        rules = random.Random(a.seed).sample(rules, min(a.sample, len(rules)))

    started = time.time()
    tally, failures = {}, []
    for rule, ds in rules:
        dtstart = datetime.strptime(ds, P.FMT)
        for name, exp in sorted(EXPANDERS.items()):
            res = P.check(exp, rule, dtstart, horizon_days=a.horizon_days,
                          cap=a.cap)
            for pid, r in res.items():
                tally.setdefault(name, {}).setdefault(pid, {})
                t = tally[name][pid]
                t[r["status"]] = t.get(r["status"], 0) + 1
                if r["status"] in (P.FAIL, P.ERROR):
                    failures.append(dict(r, expander=name, property=pid,
                                         rrule=rule, dtstart=ds))

    report = {
        "generated_by": "src/run_properties.py",
        "bounds": {"horizon_days": a.horizon_days, "cap": a.cap,
                   "note": "harness bounds, not properties of the rules"},
        "n_rules": len(rules),
        "elapsed_seconds": round(time.time() - started, 1),
        "properties": [{"id": p.id, "name": p.__name__, "hedged": p.hedged,
                        "rfc_lines": p.lines, "quote": p.quote}
                       for p in P.PROPERTIES],
        "tally": tally,
        "failures": failures,
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")
    print("%d rules, %d failures -> %s (%.0fs)"
          % (len(rules), len(failures), a.out, report["elapsed_seconds"]))
    for name in sorted(tally):
        for pid in sorted(tally[name]):
            print("  %-9s %s %s" % (name, pid, dict(tally[name][pid])))
    return 0


if __name__ == "__main__":
    sys.exit(main())

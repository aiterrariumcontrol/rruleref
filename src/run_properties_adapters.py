"""Run the metamorphic properties against a conformance adapter.

`src/run_properties.py` does this for the two in-process Python expanders.
This does it for the nine builds reachable over the adapter protocol, which is
the point of having properties at all: a property is a relation between two
expansions, so checking one needs no expected value from this repository and
no permission from anyone.

The batching and the horizon escalation are in `src/adapter_expanders.py`;
this is the fixpoint driver. A pass that recorded any cache miss is discarded
and re-run, and only a pass with **zero misses** is reported.

    python3 src/run_properties_adapters.py --adapter icaljs [--sample N]
    python3 src/run_properties_adapters.py --adapter all
"""
import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.path.dirname(HERE)
import properties as P
import adapter_expanders as A
from run_properties import load_rules

MAX_ROUNDS = 12


def sweep(exp, rules, horizon_days, cap, verbose=True):
    """Replay the property pass until it needs nothing new. Returns the pass."""
    for attempt in range(1, MAX_ROUNDS + 1):
        exp.misses = 0
        tally, failures = {}, []
        for rule, ds in rules:
            dtstart = datetime.strptime(ds, P.FMT)
            res = P.check(exp, rule, dtstart, horizon_days=horizon_days,
                          cap=cap)
            for pid, r in res.items():
                t = tally.setdefault(pid, {})
                t[r["status"]] = t.get(r["status"], 0) + 1
                if r["status"] in (P.FAIL, P.ERROR):
                    failures.append(dict(r, property=pid, rrule=rule,
                                         dtstart=ds))
        if exp.misses == 0:
            return tally, failures, attempt
        if verbose:
            print("    pass %d: %d misses, %d keys to resolve"
                  % (attempt, exp.misses, len(exp.pending)), flush=True)
        exp.resolve()
    raise SystemExit("%s: no fixpoint after %d passes (%d misses left)"
                     % (exp.name, MAX_ROUNDS, exp.misses))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True,
                    help="an id from adapter_expanders.REGISTRY, or 'all'")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--horizon-days", type=int, default=P.HORIZON_DAYS)
    ap.add_argument("--cap", type=int, default=P.CAP)
    ap.add_argument("--timeout", type=float, default=3600,
                    help="per adapter subprocess, not for the whole sweep")
    ap.add_argument("--out", default=os.path.join(
        REPO, "findings", "data", "properties-adapters.json"))
    a = ap.parse_args(argv)

    names = sorted(A.REGISTRY) if a.adapter == "all" else a.adapter.split(",")
    rules = load_rules()
    if a.sample:
        rules = random.Random(a.seed).sample(rules, min(a.sample, len(rules)))

    out = {
        "generated_by": "src/run_properties_adapters.py",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bounds": {"horizon_days": a.horizon_days, "cap": a.cap,
                   "sample": a.sample or None, "seed": a.seed,
                   "note": "harness bounds, not properties of the rules"},
        "n_rules": len(rules),
        "properties": [{"id": p.id, "name": p.__name__, "hedged": p.hedged,
                        "rfc_lines": p.lines, "quote": p.quote}
                       for p in P.PROPERTIES],
        "adapters": {},
    }
    if os.path.exists(a.out):           # merge, so one adapter can be re-run
        try:
            prev = json.load(open(a.out))
            out["adapters"] = prev.get("adapters", {})
        except Exception:
            pass

    for name in names:
        print("%s:" % name, flush=True)
        exp = A.AdapterExpander(name, cap=a.cap, timeout=a.timeout)
        t0 = time.time()
        tally, failures, passes = sweep(exp, rules, a.horizon_days, a.cap)
        out["adapters"][name] = {
            "argv": A.REGISTRY[name]["argv"],
            "n_rules": len(rules),
            "passes": passes,
            "adapter_rounds": exp.rounds,
            "adapter_requests": exp.requests,
            "distinct_keys": len(exp.cache),
            "adapter_seconds": round(exp.adapter_seconds, 1),
            "elapsed_seconds": round(time.time() - t0, 1),
            "tally": tally,
            "failures": failures,
        }
        print("  %d rules, %d passes, %d adapter rounds, %d requests, %.0fs"
              % (len(rules), passes, exp.rounds, exp.requests,
                 time.time() - t0), flush=True)
        for pid in sorted(tally):
            print("    %s %s" % (pid, dict(tally[pid])), flush=True)
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, "w") as f:
            json.dump(out, f, indent=1, sort_keys=True)
            f.write("\n")
    print("-> %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

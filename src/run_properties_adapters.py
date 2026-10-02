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

An expensive adapter can be swept across several runs (finding 120):

    python3 src/run_properties_adapters.py --adapter dtical \
        --cache scratch/property-cache --chunk 200 --budget 1800

`--cache` persists answers per adapter and refuses a cache written by a
different build; `--chunk` makes progress durable part-way through a round; and
`--budget` stops without writing a row, because a pass that still has misses
answered some properties from the placeholder and its tally would be a figure
computed from a lie.
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


class Budget(Exception):
    """The adapter time budget ran out before a zero-miss pass.

    Deliberately not a result. A pass that still had misses answered some
    properties from the placeholder `[]`, so reporting its tally would be
    reporting a number computed from a lie. With a cache attached the adapter
    time is kept and the next run starts from it; without one it is lost.
    """


def sweep(exp, rules, horizon_days, cap, verbose=True, budget=0):
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
        if budget and exp.adapter_seconds >= budget:
            raise Budget("%s: %.0fs of adapter time spent, budget %.0fs, "
                         "%d keys still unresolved"
                         % (exp.name, exp.adapter_seconds, budget,
                            len(exp.pending)))
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
    ap.add_argument("--cache", metavar="DIR",
                    help="persist each adapter's answers under DIR so an "
                         "interrupted sweep resumes instead of restarting")
    ap.add_argument("--cache-reset", action="store_true",
                    help="discard an existing cache for these adapters first")
    ap.add_argument("--chunk", type=int, default=0, metavar="N",
                    help="keys per adapter call; flushes the cache after "
                         "each, so progress survives an interruption")
    ap.add_argument("--budget", type=float, default=0, metavar="SECONDS",
                    help="stop after this much adapter time without writing a "
                         "result; the cache keeps the work for the next run")
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

    incomplete = []
    for name in names:
        print("%s:" % name, flush=True)
        exp = A.AdapterExpander(name, cap=a.cap, timeout=a.timeout,
                                chunk=a.chunk)
        if a.cache:
            os.makedirs(a.cache, exist_ok=True)
            path = os.path.join(a.cache, "%s.jsonl" % name)
            n = exp.attach_cache(path, reset=a.cache_reset)
            print("  cache %s: %d keys loaded" % (path, n), flush=True)
        t0 = time.time()
        try:
            tally, failures, passes = sweep(exp, rules, a.horizon_days, a.cap,
                                            budget=a.budget)
        except Budget as exc:
            exp.close()
            print("  %s" % exc, flush=True)
            print("  no result written for %s; %d keys cached, %.0fs adapter "
                  "time kept" % (name, len(exp.cache), exp.adapter_seconds),
                  flush=True)
            incomplete.append(name)
            continue
        exp.close()
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
    if incomplete:
        print("incomplete (budget), no row written: %s" % ", ".join(incomplete))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Measure what the dtical property column actually costs, and extrapolate.

Finding 120. The point is the *rate*, not a full column: run the property sweep
over a small sample of the corpus against the `dtical` adapter, count requests
and adapter seconds, and scale to the whole rule set. Every figure printed here
is computed from this run.

The second half checks the thing that makes the figure spendable rather than
merely large: a persisted cache replays the same sweep with zero adapter calls.

    python3 findings/repro/120-the-cost-of-the-missing-column.py [--sample N]

With the default sample this is about five minutes of Perl. Pass --sample 24 to
reproduce the figure quoted in the finding (~18 minutes).
"""
import argparse
import json
import os
import random
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

import properties as P
import adapter_expanders as A
from run_properties import load_rules
from run_properties_adapters import sweep

ap = argparse.ArgumentParser()
ap.add_argument("--sample", type=int, default=8)
ap.add_argument("--seed", type=int, default=7)
a = ap.parse_args()

allrules = load_rules()
rules = random.Random(a.seed).sample(allrules, a.sample)
tmp = tempfile.mkdtemp(prefix="120-")
try:
    cache = os.path.join(tmp, "dtical.jsonl")
    exp = A.AdapterExpander("dtical")
    exp.attach_cache(cache)
    print("build identity, which is what the cache is keyed on:")
    for part in exp.fingerprint()[1]:
        if part.startswith(("version=", "file:", "name=")):
            print("  %s" % part)
    t0 = time.time()
    tally, failures, passes = sweep(exp, rules, P.HORIZON_DAYS, P.CAP,
                                    verbose=False)
    wall = time.time() - t0
    exp.close()

    per_rule = exp.requests / float(a.sample)
    per_req = exp.adapter_seconds / float(exp.requests)
    print("")
    print("%d of %d rules, %d passes, %d adapter rounds"
          % (a.sample, len(allrules), passes, exp.rounds))
    print("  %d requests  = %.1f per rule" % (exp.requests, per_rule))
    print("  %.1fs adapter, %.1fs wall  = %.2fs per request"
          % (exp.adapter_seconds, wall, per_req))
    print("")
    full_req = per_rule * len(allrules)
    full_s = full_req * per_req
    print("extrapolated to the whole rule set (%d rules):" % len(allrules))
    print("  %.0f requests, %.0fs = %.1f hours of adapter time"
          % (full_req, full_s, full_s / 3600.0))
    print("")

    warm = A.AdapterExpander("dtical")
    loaded = warm.attach_cache(cache)
    t1 = time.time()
    t2, f2, p2 = sweep(warm, rules, P.HORIZON_DAYS, P.CAP, verbose=False)
    print("replayed from the cache: %d records loaded, %d adapter calls, "
          "%d requests, %.2fs" % (loaded, warm.rounds, warm.requests,
                                  time.time() - t1))
    same = (t2 == tally
            and sorted((f["property"], f["rrule"], f["dtstart"])
                       for f in f2)
            == sorted((f["property"], f["rrule"], f["dtstart"])
                      for f in failures))
    print("same tally and same failing triples: %s" % same)
    warm.close()
    if warm.rounds or not same:
        print("CACHE IS NOT AN EQUIVALENCE -- do not trust a cached column")
        sys.exit(1)
    print("")
    print("tally on this sample (NOT a published column -- n=%d):" % a.sample)
    for pid in sorted(tally):
        print("  %s %s" % (pid, json.dumps(tally[pid], sort_keys=True)))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

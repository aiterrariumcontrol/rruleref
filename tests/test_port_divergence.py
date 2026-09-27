#!/usr/bin/env python3
"""Finding 110's prediction still reproduces rrule.js, and its artifact is current.

110 claims that rrule.js 2.8.1's behaviour over this corpus IS
python-dateutil 2.9.0.post0's with three constructs changed, and it checks that
by patching the vendored parent and requiring the result to reproduce rrule.js
on all 1727 cases -- not only on the 28 it fails. That claim has three ways to
lapse without looking wrong, so it gets a test rather than a page:

* the vendored parent could move under the textual patches (the script exits
  loudly if an anchor stops occurring exactly once);
* the corpus could move, changing which cases are in the fail bucket;
* `findings/data/110-rrulejs-port-divergence.json` could be left behind by a
  later edit. Rule 115 -- a producer with two outputs is guarded on the one you
  check -- so `--check` diffs the stored artifact against a fresh computation
  and this test runs that mode.

rrule.js is the optional third witness (src/env.node_dir), so an unprovisioned
checkout skips rather than fails. Runs in about five seconds.
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import env

if env.node_dir() is None:
    print("skip  rrule.js is not provisioned; finding 110 has nothing to predict")
    sys.exit(0)

r = subprocess.run([sys.executable, "findings/repro/110-port-divergence-predictor.py",
                    "--check"], cwd=ROOT, capture_output=True, text=True,
                   env=dict(os.environ, TZ="UTC"))
if r.returncode != 0:
    sys.stdout.write(r.stdout)
    sys.stdout.write(r.stderr)
    print("FAIL finding 110's prediction or its stored artifact no longer holds")
    sys.exit(1)
print("ok  110's patched parent still reproduces rrule.js on every case")

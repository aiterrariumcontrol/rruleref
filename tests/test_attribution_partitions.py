#!/usr/bin/env python3
"""The published attribution maps are still partitions, and every id named by
more than one finding is still adjudicated.

Finding 109. Three findings publish a per-defect id map covering an
implementation's whole `fail` bucket -- 076 (sabre, 980), 075 (ical4j, 230), and
074 with 071 (ical.js, 236). The audit checks each is an exact partition, then
sweeps every id named in findings/*.md and in the claim lists stored under
findings/data/ and requires a verdict for every id two findings both name.

A failure here is nearly always the same event: a new finding names a case that
an older finding already counts, and nobody said which of them owns it. That is
rule 113, and the cheapest place to notice it is here rather than in a count
three findings downstream.

This runs the audit's `--no-adapters` mode, which is stored data only -- no
adapter, no scoring, deterministic. The full mode re-measures the three fail
buckets and is too slow for the suite.
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

r = subprocess.run([sys.executable,
                    "findings/repro/109-attribution-partition-audit.py",
                    "--no-adapters"], cwd=ROOT, capture_output=True, text=True)
if r.returncode != 0:
    sys.stdout.write(r.stdout)
    sys.stdout.write(r.stderr)
    print("FAIL the attribution audit has a failing check")
    sys.exit(1)
for line in r.stdout.splitlines():
    if "distinct cases appear" in line or "are named by a finding" in line:
        print(line.strip())
print("ok  the three attribution maps are partitions and every shared id is "
      "adjudicated")

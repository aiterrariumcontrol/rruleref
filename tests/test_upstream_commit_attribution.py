#!/usr/bin/env python3
"""Finding 113 still holds: one upstream commit, thirteen cases, no regression.

113 attributes the whole of libical master's 19 -> 6 `fail` improvement to the
single commit `4edd39a` ("BYSETPOS issue fix", #1387), and inherits the six that
remain from finding 112 rather than re-deriving them. Ways that can lapse:

* any of the three builds could drift -- a reconfigured prefix, a different ICU,
  a rebuilt adapter -- which shows up as a count or an id set that moved;
* the 13 + 6 split could stop partitioning `48d52b4b`'s bucket, which is the
  same property finding 109's audit checks for the published maps;
* 112's two defect sites could stop being textually identical across the range,
  which would invalidate reusing 112's labels here;
* the stored artifact could fall behind the script -- rule 115.

Three install prefixes are needed and none is in the tree, so an unprovisioned
checkout skips rather than fails. Runs three scoring passes, about 40s.
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.environ.get("LIBICAL_SCRATCH", "/home/agent/terrarium/scratch")
NEEDED = ["libical-install", "libical-install-cefc9ca", "libical-install-4edd"]

absent = [n for n in NEEDED
          if not os.path.isdir(os.path.join(SCRATCH, n, "lib"))]
if absent:
    print("skip  no libical builds for %s; finding 113 has nothing to check"
          % ", ".join(absent))
    sys.exit(0)

r = subprocess.run([sys.executable,
                    "findings/repro/113-one-commit-thirteen-cases.py", "--check"],
                   cwd=ROOT, capture_output=True, text=True,
                   env=dict(os.environ, TZ="UTC"))
if r.returncode != 0:
    sys.stdout.write(r.stdout)
    sys.stdout.write(r.stderr)
    print("FAIL finding 113's attribution or its stored artifact no longer holds")
    sys.exit(1)
print("ok  113 still attributes 13 cases to one commit, with 6 left to 112")

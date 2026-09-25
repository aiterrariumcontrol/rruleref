#!/usr/bin/env python3
"""Every baselined reproduce command still prints what it printed when published.

Finding 092. Finding 031 documented a script and a table; the script kept
exiting 0 while the corpus moved underneath it, and two rows of the table were
wrong for five days with nothing to notice. This test is the thing that would
have noticed.

A failure here is not automatically a bug in the code. It means a published
figure and its producer no longer agree, and somebody has to decide which one is
right before re-baselining with `tools/check_repro_drift.py --update`.
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

r = subprocess.run([sys.executable, "tools/check_repro_drift.py"],
                   cwd=ROOT, capture_output=True, text=True)
sys.stdout.write(r.stdout)
sys.stdout.write(r.stderr)
if r.returncode != 0:
    print("FAIL a baselined reproduce command no longer matches its baseline")
    sys.exit(1)
print("ok  every baselined reproduce command matches")

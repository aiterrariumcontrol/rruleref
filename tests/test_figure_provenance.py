#!/usr/bin/env python3
"""Every provenance declaration in the findings still applies.

Finding 093. Findings annotate their unbacked figures in their own markdown --
`<!-- provenance: TIMING 0.022 -- wall-clock -->` -- so that the audit can say
which of its NOWHERE figures are answers and which are debts.

An annotation that silences an audit is a way to make the audit lie. This test
is what stops that: the audit exits non-zero when a declaration names a figure
that is no longer unbacked in that finding, when a DERIVED figure can no longer
be recomputed from an `(a of b)` on its own line, or when a QUOTED figure's
source finding no longer publishes it.

A failure here is usually not a bug in the code. It means a finding was edited
and its annotation was not, and somebody has to look at the figure.
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

r = subprocess.run([sys.executable, "findings/repro/091-figure-provenance-audit.py"],
                   cwd=ROOT, capture_output=True, text=True)
if r.returncode != 0:
    sys.stdout.write(r.stdout)
    sys.stdout.write(r.stderr)
    print("FAIL a provenance declaration no longer applies")
    sys.exit(1)
# Report the debt, which is the number worth watching.
for line in r.stdout.splitlines():
    if "DEBT" in line or "debt total" in line:
        print(line.rstrip())
print("ok  every provenance declaration still applies")

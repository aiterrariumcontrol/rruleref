#!/usr/bin/env python3
"""Finding 112 still reproduces libical, and its artifact is current.

112 claims that libical master 4edd39a3's whole six-case `fail` bucket is two
BYWEEKNO defects, four and two. Ways for that to lapse without looking wrong:

* either defect could be fixed upstream, which shows up as the short weeks
  becoming seven days long, or as the live fail bucket shrinking below the map;
* the map could stop being a partition of the live bucket, which is what
  finding 109's audit exists to catch and is re-checked here directly;
* the artifact under findings/data/ could be left behind by a later edit --
  rule 115 -- so the run diffs the stored file against a fresh computation.

The libical shared library is not in the tree (the published libical rows name
the prefix they were measured through), so an unprovisioned checkout skips
rather than fails. The rebuild-and-patch half of the repro is NOT run here: it
needs cmake and a source checkout, and it writes install prefixes. About 25s.
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.environ.get("LIBICAL_LIB",
                     "/home/agent/terrarium/scratch/libical-install-4edd")

if not os.path.isdir(os.path.join(LIB, "lib")):
    print("skip  no libical build at %s; finding 112 has nothing to check" % LIB)
    sys.exit(0)

r = subprocess.run([sys.executable,
                    "findings/repro/112-libical-week-start-blind.py", "--check"],
                   cwd=ROOT, capture_output=True, text=True,
                   env=dict(os.environ, TZ="UTC"))
if r.returncode != 0:
    sys.stdout.write(r.stdout)
    sys.stdout.write(r.stderr)
    print("FAIL finding 112's measurement or its stored artifact no longer holds")
    sys.exit(1)
print("ok  112 still reproduces libical's two BYWEEKNO defects and their partition")

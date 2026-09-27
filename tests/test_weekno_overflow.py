#!/usr/bin/env python3
"""Finding 111 still reproduces dmfs lib-recur, and its artifact is current.

111 claims that dmfs lib-recur 0.17.1 emits an instance at December 32nd when
BYWEEKNO names a week the year does not have, and partitions the adapter's
four-case `fail` bucket on the strength of that. Four ways for the claim to
lapse without looking wrong:

* the defect could be fixed upstream, which shows up as short years starting to
  yield nothing;
* one of the three observables (the six-day week, the 52/53 collision, the
  BYDAY monotonicity break) could stop reproducing;
* a necessity comparison could stop agreeing, which would mean the week-53
  branch was never the whole cause of that case;
* the artifact under findings/data/ could be left behind by a later edit --
  rule 115, a producer with two outputs is guarded on the one you check -- so
  --check diffs the stored file against a fresh computation.

The JVM and the compiled adapter classes are optional here, as node is for
finding 110, so an unprovisioned checkout skips rather than fails. Runs in
about a second.
"""
import os, subprocess, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASSES = os.path.join(ROOT, "conformance", "adapters", "java", "classes")

if shutil.which("java") is None or not os.path.isfile(
        os.path.join(CLASSES, "DmfsAdapter.class")):
    print("skip  no JVM or no compiled dmfs adapter; finding 111 has nothing to check")
    sys.exit(0)

r = subprocess.run([sys.executable, "findings/repro/111-dmfs-weekno-overflow.py",
                    "--check"], cwd=ROOT, capture_output=True, text=True,
                   env=dict(os.environ, TZ="UTC"))
if r.returncode != 0:
    sys.stdout.write(r.stdout)
    sys.stdout.write(r.stderr)
    print("FAIL finding 111's measurement or its stored artifact no longer holds")
    sys.exit(1)
print("ok  111 still reproduces dmfs's week-53 overflow and its partition")

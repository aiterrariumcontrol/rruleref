"""Every scored row published in RESULTS.md sums to the corpus's case count.

A row of a scoring table partitions the same case set, so its buckets must add
up. Three published rows did not, and none was caught by reading: `ical4j`'s
main row summed to 1726 (finding 075), `rrule-go`'s to 1724 because one of the
scorer's six buckets has no column, and the JVM-locale table's three rows to
1659/1658/1658 because that table was a measurement of the corpus as it stood
before 2026-09-20 and nothing re-ran it when the corpus moved (finding 077).

This is in the suite rather than in a note telling me to remember, for the same
reason test_links.py is: the failure mode is that the author rereads the page
many times without adding the cells up. It is also why the check is bound to the
*live* count in cases.ndjson rather than to a literal — the locale table was
correct on the day it was written.

The check is exactly tools/check_results_rows.py, run as a subprocess so that
the command a stranger types and the command CI runs are the same one.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

r = subprocess.run(
    [sys.executable, os.path.join(ROOT, "tools", "check_results_rows.py")],
    capture_output=True, text=True)
sys.stdout.write(r.stdout)
sys.stderr.write(r.stderr)
if r.returncode != 0:
    print("FAIL: a published row does not account for the whole case set.")
    sys.exit(1)
print("OK")

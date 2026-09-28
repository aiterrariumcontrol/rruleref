"""Every documented per-case deadline matches the adapter source that implements it.

A per-case deadline is an instrument parameter: it decides which cases land in
`error` rather than `fail`, and finding 047 measured 146 errors at 20 s against
133 at 120 s over the same cases. `conformance/adapters/perl/README.md` said 10
seconds where the adapter has always said 20, and finding 073 -- the finding
about which `error` cells are the clock -- copied the value out of that README
instead of the source. Finding 114.

This is in the suite and not in a note reminding me to check, because the
failure mode is reading prose about the source instead of the source. The same
reason test_links.py and test_results_rows.py are here.

The check is exactly tools/check_adapter_deadlines.py, run as a subprocess so
that the command a stranger types and the command CI runs are the same one.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

r = subprocess.run(
    [sys.executable, os.path.join(ROOT, "tools", "check_adapter_deadlines.py")],
    capture_output=True, text=True)
sys.stdout.write(r.stdout)
sys.stderr.write(r.stderr)
if r.returncode != 0:
    print("FAIL: a documented per-case deadline disagrees with its adapter.")
    sys.exit(1)
print("OK")

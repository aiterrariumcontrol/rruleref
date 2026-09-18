"""Every relative Markdown link in README.md, RESULTS.md and findings/ resolves.

Two broken links shipped in published findings before anyone looked: finding 052
pointed at a filename 051 never had, and 048 at ../PROTOCOL.md when PROTOCOL.md
lives under conformance/. Both survived because a dead relative link in a
Markdown file is invisible until a reader clicks it, and the reader who clicks
it is not the author. So the check belongs in the suite rather than in a note
telling me to remember.

The check is exactly tools/check_links.py, run as a subprocess so that the
command a stranger types and the command CI runs are the same one.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_links.py")],
                   capture_output=True, text=True)
sys.stdout.write(r.stdout)
sys.stderr.write(r.stderr)
if r.returncode != 0:
    print("FAIL: a relative Markdown link does not resolve (see above).")
    sys.exit(1)
print("OK")

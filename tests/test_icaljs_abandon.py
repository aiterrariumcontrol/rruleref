"""Finding 103 as a debugger diagnostic, and the predictor that backs it.

`web/src/diagnostics.js` now warns, on the user's own rule, when `ical.js`
2.2.1 will stop the series early and report no error: it abandons a
`FREQ=YEARLY` expansion after 28 consecutive iterations that produce no
occurrence. A warning like that is worth nothing unless it is right about
*where* the series stops, so the diagnostic does not match a shape -- it
predicts the exact prefix ical.js returns, and `web/test/icaljs-yearly-abandon.mjs`
requires that prediction to reproduce ical.js's real output byte for byte on
every rule it is given, firing and not firing alike.

This wrapper exists so the prediction is checked by the ordinary suite rather
than only when I remember to run node by hand. It skips, loudly, when node or
the npm-installed ical.js is absent -- the harness needs the real library,
not a model of it.
"""
import os
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HARNESS = os.path.join(ROOT, "web", "test", "icaljs-yearly-abandon.mjs")
ICALJS = os.path.join(ROOT, "js", "node_modules", "ical.js")


def main():
    if not shutil.which("node"):
        print("SKIP: node is not installed; the predictor cannot be run against ical.js")
        return 0
    if not os.path.isdir(ICALJS):
        print("SKIP: js/node_modules/ical.js is absent (run tools/bootstrap.sh);")
        print("      this check compares the diagnostic against the real library only")
        return 0

    r = subprocess.run(["node", HARNESS], capture_output=True, text=True, cwd=ROOT)
    print(r.stdout.rstrip())
    if r.returncode != 0:
        print("\nFAILED: the harness exited %d" % r.returncode)
        if r.stderr.strip():
            print(r.stderr.strip()[-1200:])
        return 1
    if "OK:" not in r.stdout:
        print("\nFAILED: the harness exited 0 without printing its OK line, which is")
        print("        how it reports that it tested nothing at all")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

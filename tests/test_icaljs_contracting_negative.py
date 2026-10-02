"""Finding 070's defect A as a debugger diagnostic, and the predictor behind it.

`web/src/diagnostics.js` now warns, on the user's own rule, when `ical.js`
2.2.1 cannot match a negative value in a `BY` part that *contracts* under the
rule's own `FREQ`. One cause, two symptoms, and which one the user gets is
computable: with another matchable value in the part the library silently
answers as though the negative had never been written, and without one the
unbounded `do ... while` in `next()` never returns, allocating until the
process dies. `FREQ=DAILY;BYMONTHDAY=-1` -- twenty-six characters, and an
ordinary way to write "the last day of every month" -- is enough.

A warning like that is worth nothing unless it is right, so the note does not
match a shape: it predicts ical.js's whole answer, and
`web/test/icaljs-contracting-negative.mjs` requires that prediction to
reproduce the real library byte for byte where a stream comes back, and to be
right about *which* rules produce no answer at all. Because a library that
aborts the process cannot be contained in-process, every case runs in its own
child with a 16 MB heap -- which turns the non-termination into a definite
SIGABRT rather than a deadline a loaded machine could also produce. That is
only cheap at FREQ=DAILY and HOURLY; the harness says so and counts the
MINUTELY and SECONDLY cases separately as the weaker observation they are.

This wrapper exists so the prediction is checked by the ordinary suite rather
than only when I remember to run node by hand. It skips, loudly, when node or
the npm-installed ical.js is absent -- the harness needs the real library, not
a model of it. It takes around two minutes, most of it waiting for heaps to
die.
"""
import os
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HARNESS = os.path.join(ROOT, "web", "test", "icaljs-contracting-negative.mjs")
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

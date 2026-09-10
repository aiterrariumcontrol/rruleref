"""The date explainer must agree with the expander it explains.

`web/src/why.js` answers "why is this date not in my list?" by running the
BY-rule predicates one at a time in the order RFC 5545 3.3.10 states, and then
reasoning separately about BYSETPOS, COUNT and UNTIL. `expand()` answers the
same question by a different route. Two routes to one answer is the shape that
goes quietly wrong, so both are run over every corpus case here: each published
occurrence must come back as an occurrence at its own index, and a spread of
near-miss dates must not.

The explainer also cross-checks itself at runtime -- if its part-by-part result
disagrees with `matches()` it says so rather than choosing -- and that state is
a failure here too.

Skips, loudly, when node is not installed.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

fails = []


def cases():
    out = []
    for name in ("corroborated", "disputed", "date-value-type"):
        path = os.path.join(ROOT, "corpus", "%s.json" % name)
        if not os.path.exists(path):
            continue
        cs = json.load(open(path))["cases"]
        for c in (cs if isinstance(cs, list) else cs.values()):
            out.append({"rrule": c["rrule"], "dtstart": c["dtstart"]})
    # Distinct (rule, dtstart) pairs only; the corpus repeats them across cells.
    seen, uniq = set(), []
    for c in out:
        k = (c["rrule"], c["dtstart"])
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    return uniq


def test_why_agrees_with_the_expander():
    cs = cases()
    r = subprocess.run(
        ["node", os.path.join(ROOT, "web", "test", "why-agreement.mjs")],
        input=json.dumps(cs), capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        fails.append("why-agreement.mjs did not run: %s" % (r.stderr.strip()[-800:]))
        return
    got = json.loads(r.stdout.strip().splitlines()[-1])
    if got["nfails"]:
        fails.append("why(): %d disagreements with the expander over %d verdicts; first:\n    %s"
                     % (got["nfails"], got["checked"], "\n    ".join(got["fails"])))
    else:
        print("  why(): %d verdicts over %d rules, all agreeing with the expander"
              % (got["checked"], len(cs)))


if __name__ == "__main__":
    if not shutil.which("node"):
        print("skip: node is not installed; the date explainer is unchecked")
        raise SystemExit(0)
    test_why_agrees_with_the_expander()
    for f in fails:
        print("FAIL: %s" % f)
    raise SystemExit(1 if fails else 0)

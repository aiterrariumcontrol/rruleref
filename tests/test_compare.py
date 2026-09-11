"""Comparing two rules must not report a difference that is an artefact of the cap.

`web/src/compare.js` answers "what did this edit do to my dates". The reason
to distrust it is specific. Both expansions stop at the occurrence count the
user asked for, and if the lists are compared past the point where the shorter
one stops, every remaining date in the longer one looks like a date the edit
added. An edit that merely made the rule fire more often would be reported as
an edit that gains dates it does not gain -- and the user would act on it.

So the properties checked over an edit generator (drop a BY part, or keep only
the first value of a multi-valued one, which is the Superset bug where
`Number.parseInt("9,17")` quietly became 9):

  PARTITION  unchanged + dropped is exactly the first expansion inside the
             window, unchanged + added is exactly the second, and the three
             lists are disjoint.

  WINDOW     re-expanding both rules with four times the cap and cutting at the
             same window gives the same three lists. If the verdict moves when
             the cap moves, the verdict was about the cap.

Seen to fail: replacing the window with Infinity makes 4579 of 4717 pairs
violate WINDOW.

Skips, loudly, when node is not installed.
"""
import json
import os
import shutil
import subprocess

fails = []

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def cases():
    out = []
    with open(os.path.join(ROOT, "conformance", "cases.ndjson")) as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def test_comparison_is_a_partition_and_does_not_depend_on_the_cap():
    r = subprocess.run(
        ["node", os.path.join(ROOT, "web", "test", "compare-consistent.mjs")],
        input=json.dumps(cases()), capture_output=True, text=True, cwd=ROOT)
    for line in r.stdout.strip().splitlines():
        print("  " + line)
    if r.returncode != 0:
        fails.append("compareRules() failed its own corpus check; see above%s"
                     % (("\n  stderr: " + r.stderr.strip()[-800:]) if r.stderr.strip() else ""))
    elif "OK:" not in r.stdout:
        fails.append("compare-consistent.mjs exited 0 without printing its OK line")


if __name__ == "__main__":
    if not shutil.which("node"):
        print("skip: node is not installed; the two-rule comparison is unchecked")
        raise SystemExit(0)
    test_comparison_is_a_partition_and_does_not_depend_on_the_cap()
    for f in fails:
        print("FAIL: " + f)
    raise SystemExit(1 if fails else 0)

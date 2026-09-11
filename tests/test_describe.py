"""The plain-English rendering must not lie by omission.

`web/src/describe.js` turns an RRULE into one English sentence. The reason to
distrust such a thing is not that the prose may be clumsy -- a reader can see
that -- but that it may silently drop the part that changes the answer, which
a reader cannot see. rrule.js's `toText()` does exactly this: over this
repository's corpus it renders `FREQ=DAILY;BYHOUR=9,8` and
`FREQ=DAILY;BYHOUR=9,8;BYSETPOS=-1` as the same sentence while reporting
itself fully convertible, and those two rules fire twice a day and once a day.

So the property checked here is injectivity against the expander: if two
corpus rules get the same sentence from the same DTSTART, they must have the
same expansion. Plus coverage: every stated RRULE part is claimed by some
clause, and no clause claims a part the rule does not state.

Neither property says the English reads well; a human judges that. They say it
is not quietly incomplete.

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


def test_describe_is_injective_against_the_expander():
    r = subprocess.run(
        ["node", os.path.join(ROOT, "web", "test", "describe-injective.mjs")],
        input=json.dumps(cases()), capture_output=True, text=True, cwd=ROOT)
    for line in r.stdout.strip().splitlines():
        print("  " + line)
    if r.returncode != 0:
        fails.append("describe() failed its own corpus check; see above%s"
                     % (("\n  stderr: " + r.stderr.strip()[-800:]) if r.stderr.strip() else ""))
    elif "OK:" not in r.stdout:
        fails.append("describe-injective.mjs exited 0 without printing its OK line")


if __name__ == "__main__":
    if not shutil.which("node"):
        print("skip: node is not installed; the plain-English rendering is unchecked")
        raise SystemExit(0)
    test_describe_is_injective_against_the_expander()
    for f in fails:
        print("FAIL: %s" % f)
    raise SystemExit(1 if fails else 0)

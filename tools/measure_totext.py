#!/usr/bin/env python3
"""How often does a plain-English rendering of an RRULE lose the answer?

`web/README.md` and `web/src/describe.js` both make a numeric claim about
rrule.js's `toText()`: that it gives the identical sentence to rules with
different occurrence sets, while reporting itself fully convertible. A claim
about somebody else's library should be reproducible by whoever reads it, so
this is the script that produces it.

Method, and its limits:

1. Take the distinct rules in `conformance/cases.ndjson`.
2. Keep the ones `rrule.js` says are `isFullyConvertibleToText()`. The ones it
   declines to render are not the interesting case -- declining is honest.
3. Group them by the sentence `toText()` returns.
4. Within each group of two or more, expand every rule from ONE COMMON
   DTSTART with this repository's own reference expander (`src/naive.py`) and
   see whether the groups' members actually agree.

Step 4 is why the common DTSTART matters: whether two rules "are the same" is
only a meaningful question once they start from the same place. A different
DTSTART or a different horizon would give a different count, so both are
printed with the result rather than left implicit.

This measures `toText()` against *this* corpus, which was built to exercise
RFC 5545 3.3.10 and is therefore denser in BYSETPOS and BYWEEKNO than ordinary
calendar data. It is not a claim about rules in the wild.

Usage: python3 tools/measure_totext.py
Requires: node, and rrule.js installed by tools/bootstrap.sh.
"""
import datetime
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import naive  # noqa: E402

DTSTART = datetime.datetime(2026, 1, 1, 9, 0, 0)
HORIZON = datetime.datetime(2031, 1, 1)
LIMIT = 40

NODE = r"""
const fs=require('fs'), path=require('path');
const {RRule}=require(path.join(process.argv[process.argv.length-1],'node_modules','rrule'));
const rules=JSON.parse(fs.readFileSync(0,'utf8'));
const out={full:[], declined:0};
for(const s of rules){
  let r; try{ r=RRule.fromString('DTSTART:20260101T090000Z\nRRULE:'+s); }catch(e){ out.declined++; continue; }
  if(!r.isFullyConvertibleToText()){ out.declined++; continue; }
  out.full.push([s, r.toText()]);
}
process.stdout.write(JSON.stringify(out));
"""


def main():
    rules, seen = [], set()
    with open(os.path.join(ROOT, "conformance", "cases.ndjson")) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            s = json.loads(line)["rrule"]
            if s not in seen:
                seen.add(s)
                rules.append(s)

    js = os.path.join(ROOT, "js")
    if not os.path.isdir(os.path.join(js, "node_modules", "rrule")):
        print("rrule.js is not installed; run tools/bootstrap.sh first")
        return 2
    r = subprocess.run(["node", "-e", NODE, "--", js], input=json.dumps(rules),
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("node failed:\n%s" % r.stderr.strip()[-2000:])
        return 2
    got = json.loads(r.stdout)

    groups = {}
    for s, text in got["full"]:
        groups.setdefault(text, []).append(s)

    shared = {t: v for t, v in groups.items() if len(v) > 1}
    ambiguous, ambiguous_rules, examples = 0, 0, []
    for text, members in shared.items():
        sets = {}
        for s in members:
            try:
                occ = tuple(naive.expand(s, DTSTART, horizon=HORIZON, limit=LIMIT))
            except Exception as e:                      # noqa: BLE001
                occ = ("ERR", str(e))
            sets.setdefault(occ, []).append(s)
        if len(sets) > 1:
            ambiguous += 1
            ambiguous_rules += len(members)
            if len(examples) < 5:
                examples.append((text, [v[0] for v in sets.values()][:3]))

    print("corpus:                       %d distinct rules" % len(rules))
    print("rrule.js declined to render:  %d" % got["declined"])
    print("reported fully convertible:   %d" % len(got["full"]))
    print("sentences given to >1 rule:   %d" % len(shared))
    print("...where the rules DIFFER:    %d groups, %d rules"
          % (ambiguous, ambiguous_rules))
    print("compared from DTSTART %s, horizon %s, first %d occurrences"
          % (DTSTART.strftime("%Y%m%dT%H%M%S"), HORIZON.strftime("%Y%m%d"), LIMIT))
    for text, members in examples:
        print("  %r" % text)
        for m in members:
            print("      %s" % m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

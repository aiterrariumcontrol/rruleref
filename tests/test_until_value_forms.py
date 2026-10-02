#!/usr/bin/env python3
"""Finding 121's UNTIL rows still hold, and its artifact still means something.

Three checks, cheap enough to keep in the gate:

1. The corpus claim the finding is built on -- that every `UNTIL` case spells
   the value one way -- is recomputed from `conformance/cases.ndjson` rather
   than quoted. If a later wake adds a date-only or UTC `UNTIL` case, finding
   121's premise has changed and this is where that surfaces.
2. `dateutil`'s committed rows are re-measured. Python only, so it runs
   anywhere; the other eight need node, java, php, perl or a libical build and
   are verified by `findings/repro/121-until-value-forms.py --check` instead.
3. The artifact's structure is pinned: both zones present, all nine builds in
   each, and -- the point of the second zone -- at least one build whose rows
   actually differ between them. A refactor that dropped the `TZ` override
   would leave every row equal and the probe would still pass; rule 135 says
   that is exactly the failure that reads as unanimity.

A few seconds.
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "findings", "data", "until-value-forms.json")
FAIL = []


def check(label, ok, detail=""):
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", label,
                           ("   -- " + detail) if detail else ""))
    if not ok:
        FAIL.append(label)


def until_form(value):
    if re.fullmatch(r"\d{8}", value):
        return "date-only"
    return "datetime-utc" if value.endswith("Z") else "datetime-local"


def main():
    print("finding 121: the UNTIL value-type rows")

    # 1. the premise
    forms = {}
    n = 0
    for line in open(os.path.join(ROOT, "conformance", "cases.ndjson")):
        c = json.loads(line)
        n += 1
        m = re.search(r"UNTIL=([^;]*)", c["rrule"])
        if m:
            forms[until_form(m.group(1))] = forms.get(until_form(m.group(1)), 0) + 1
    check("every corpus UNTIL case is a floating DATE-TIME",
          list(forms) == ["datetime-local"],
          "%d of %d cases use UNTIL, forms=%s" % (sum(forms.values()), n, forms))

    # 2. and 3. the artifact
    d = json.load(open(DATA))
    runs = d.get("runs", {})
    check("both ambient zones are in the artifact",
          sorted(runs) == ["America/Chicago", "UTC"], str(sorted(runs)))
    sizes = {tz: len(runs[tz]) for tz in runs}
    check("nine builds in every zone", set(sizes.values()) == {9}, str(sizes))

    if len(runs) == 2:
        a, b = sorted(runs)
        movers = [name for name in runs[a]
                  if runs[a][name]["rows"] != runs[b].get(name, {}).get("rows")]
        check("the second zone separates at least one build (rule 135)",
              len(movers) >= 1, "builds whose rows move: %s" % sorted(movers))

    r = subprocess.run([sys.executable,
                        "findings/repro/121-until-value-forms.py",
                        "--adapter", "dateutil", "--check"],
                       cwd=ROOT, capture_output=True, text=True)
    check("dateutil's committed rows re-measure identically", r.returncode == 0,
          (r.stdout + r.stderr).strip().splitlines()[-1] if r.stdout or r.stderr
          else "")

    print("%d failed" % len(FAIL) if FAIL else "all ok")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())

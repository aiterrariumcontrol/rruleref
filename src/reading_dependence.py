"""Which corroborated cases would change answer under the other reading?

`corpus/disputed.json` holds the cases where `src/naive.py` and the pinned
`python-dateutil` return different occurrence lists. That is a test of
*implementation agreement*. It is not a test of whether a case's expected
value is *contested*, and the two come apart: two implementations can agree
and still both be making the choice finding 004 says is disputed.

This module asks the second question directly. For every corroborated case
carrying BYSETPOS it expands the rule twice --

  * BYSETPOS selects from the whole period, instances before DTSTART are then
    dropped (`naive.expand`'s normal reading), and
  * the period containing DTSTART is cut at DTSTART first, so BYSETPOS=1 can
    name DTSTART itself (`truncate_first_period=True`)

-- and reports the cases whose first `len(expect)` occurrences differ. Those
cases are *reading-dependent*: the corpus commits them to one reading of
RFC 5545 3.3.10 without saying so.

    python3 src/reading_dependence.py [--json findings/data/018-reading-dependence.json]

Written for finding 018. The count it produced on 2026-09-07 is 54 of 677
BYSETPOS cases, every one of them recording the untruncated reading.
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import naive  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _parse(s):
    s = s.rstrip("Z")
    return datetime.strptime(s, "%Y%m%dT%H%M%S" if "T" in s else "%Y%m%d")


def analyse(cases):
    """Return (n_setpos, rows) for the reading-dependent cases in `cases`."""
    rows, n_setpos = [], 0
    for c in cases:
        if "BYSETPOS" not in c["rrule"]:
            continue
        n_setpos += 1
        ds = _parse(c["dtstart"])
        n = len(c["expect"])
        # A date-valued DTSTART must come back date-valued; the corpus's
        # expected strings are compared byte for byte.
        pat = "%Y%m%dT%H%M%S" if "T" in c["dtstart"] else "%Y%m%d"
        whole = [x.strftime(pat) for x in naive.expand(c["rrule"], ds, limit=n)][:n]
        cut = [x.strftime(pat) for x in
               naive.expand(c["rrule"], ds, limit=n, truncate_first_period=True)][:n]
        if whole == cut:
            continue
        rows.append({
            "rrule": c["rrule"],
            "dtstart": c["dtstart"],
            "expect": c["expect"],
            "whole_period": whole,
            "first_period_truncated": cut,
            # Which reading the published corpus actually recorded. If this is
            # ever "neither", the expander and the corpus have drifted apart
            # and the corpus is the thing to distrust.
            "corpus_records": ("whole_period" if c["expect"] == whole else
                               "first_period_truncated" if c["expect"] == cut
                               else "neither"),
            "dtstart_synchronized": c.get("dtstart_synchronized"),
            "freq": c["rrule"].split(";")[0],
        })
    return n_setpos, rows


def main(dest=None):
    blob = json.load(open(os.path.join(REPO, "corpus", "corroborated.json")))
    cases = blob["cases"] if isinstance(blob, dict) else blob
    n_setpos, rows = analyse(cases)
    from collections import Counter
    print("corroborated cases      : %d" % len(cases))
    print("carrying BYSETPOS       : %d" % n_setpos)
    print("reading-dependent       : %d" % len(rows))
    print("corpus records          : %s"
          % dict(Counter(r["corpus_records"] for r in rows)))
    print("by FREQ                 : %s"
          % dict(Counter(r["freq"] for r in rows)))
    if dest:
        json.dump({"meta": {"corroborated": len(cases), "with_bysetpos": n_setpos,
                            "reading_dependent": len(rows)},
                   "cases": rows}, open(dest, "w"), indent=1, sort_keys=True)
        print("-> %s" % dest)
    return 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    out = argv[argv.index("--json") + 1] if "--json" in argv else None
    sys.exit(main(out))

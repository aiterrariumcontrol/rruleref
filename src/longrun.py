"""Cross-expander differential far past the corpus's eight-occurrence window.

Every expected value in the corpus describes one short window near DTSTART.
Two expanders can agree on all of them and diverge in year three, and nothing
in this repository would have noticed. This runs both expanders over every
synchronized corpus rule for a three-year horizon and reports every point of
disagreement.

Its first run (2026-09-07) found 11, all at the horizon edge, all BYSETPOS,
and all one defect in `naive`: the caller's horizon was cutting the candidate
stream before BYSETPOS selected from the final period, so the last occurrence
returned could be one no complete expansion contains. See findings/014. After
the fix: 0 of 1,722.

    python3 src/longrun.py [--horizon-days N] [--cap N] [--out PATH]
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.path.dirname(HERE)
import properties as P
from expanders import naive_expander, dateutil_expander
from run_properties import load_rules


def diverge(rules, horizon_days, cap):
    out = []
    for rule, ds in rules:
        d0 = datetime.strptime(ds, P.FMT)
        h = d0 + timedelta(days=horizon_days)
        a = naive_expander(rule, d0, h, cap)
        b = dateutil_expander(rule, d0, h, cap)
        capped = len(a) >= cap or len(b) >= cap
        if capped:
            # A cap is mine, not the rule's: compare only where both are whole.
            edge = min(a[-1] if a else h, b[-1] if b else h)
            a = [t for t in a if t <= edge]
            b = [t for t in b if t <= edge]
        if a == b:
            continue
        i = next((j for j in range(min(len(a), len(b))) if a[j] != b[j]),
                 min(len(a), len(b)))
        out.append({"rrule": rule, "dtstart": ds, "capped": capped,
                    "first_diff_index": i, "n_naive": len(a),
                    "n_dateutil": len(b),
                    "naive": [t.strftime(P.FMT) for t in a[max(0, i - 1):i + 3]],
                    "dateutil": [t.strftime(P.FMT) for t in b[max(0, i - 1):i + 3]]})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon-days", type=int, default=365 * 3)
    ap.add_argument("--cap", type=int, default=3000)
    ap.add_argument("--out", default=os.path.join(
        REPO, "findings", "data", "longrun-divergence.json"))
    a = ap.parse_args(argv)
    rules = load_rules()
    div = diverge(rules, a.horizon_days, a.cap)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump({"horizon_days": a.horizon_days, "cap": a.cap,
                   "note": "horizon and cap bound the harness, not the rules",
                   "n_rules": len(rules), "divergences": div},
                  f, indent=1, sort_keys=True)
        f.write("\n")
    print("%d rules, %d divergences beyond the corpus window -> %s"
          % (len(rules), len(div), a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

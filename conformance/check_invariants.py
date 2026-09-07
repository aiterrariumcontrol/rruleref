"""Run an adapter and report occurrences that violate the rule's own BY parts.

    python3 conformance/check_invariants.py -- <adapter command>

Never consults `expect`, so a *guaranteed* violation is a conformance claim that
does not depend on this corpus being right. Order-dependent mismatches are
counted separately and are not claims; see invariants.py.

Exit status is 1 only when a guaranteed violation was found.
"""
import argparse, collections, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import invariants

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=os.path.join(REPO, "conformance", "cases.ndjson"))
    ap.add_argument("--json", help="write every violating case here")
    ap.add_argument("cmd", nargs="+")
    a = ap.parse_args(argv)
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd

    cases = [json.loads(l) for l in open(a.cases) if l.strip()]
    stdin = "".join(json.dumps({k: c[k] for k in ("id", "rrule", "dtstart", "limit")}) + "\n"
                    for c in cases)
    out = subprocess.run(cmd, input=stdin, capture_output=True, text=True).stdout
    replies = {}
    for line in out.splitlines():
        if line.strip():
            r = json.loads(line)
            replies[r["id"]] = r

    by_part = {True: collections.Counter(), False: collections.Counter()}
    hard, soft, missing = [], [], 0
    for c in cases:
        r = replies.get(c["id"])
        if r is None:
            missing += 1
            continue
        occ = r.get("occurrences")
        if not occ:
            continue
        vs = list(invariants.violations(c["rrule"], occ))
        if not vs:
            continue
        for _, part, _, g in vs:
            by_part[g][part] += 1
        row = {"case": c, "occurrences": occ,
               "violations": [{"occurrence": o, "part": p, "detail": d, "guaranteed": g}
                              for o, p, d, g in vs]}
        (hard if any(g for _, _, _, g in vs) else soft).append(row)

    print("adapter: %s" % " ".join(cmd))
    print("cases:   %d%s" % (len(cases), "  (%d unanswered)" % missing if missing else ""))
    print("  guaranteed violations       %d cases  %s"
          % (len(hard), dict(by_part[True]) or "none"))
    print("  order-dependent mismatches  %d cases  %s   (not a claim; see invariants.py)"
          % (len(soft), dict(by_part[False]) or "none"))
    if a.json:
        json.dump({"adapter": cmd,
                   "guaranteed": {"cases": len(hard), "by_part": dict(by_part[True])},
                   "order_dependent": {"cases": len(soft), "by_part": dict(by_part[False])},
                   "detail_guaranteed": hard, "detail_order_dependent": soft},
                  open(a.json, "w"), indent=1)
        print("full result -> %s" % a.json)
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())

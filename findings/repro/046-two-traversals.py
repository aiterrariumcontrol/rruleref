"""Reproduce finding 046: DateTime::Set's ->iterator and repeated ->next disagree.

    python3 findings/repro/046-two-traversals.py --out findings/data/046-two-traversals.json

Finding 046 published a three-by-three table and the count "68 of the 291
cases return different answers under the two traversals", and saved neither the
data nor the script that produced them. Rule 79 says a derived count is only
published with its derivation beside it. This is that derivation, written
afterwards.

Method, as 046 describes it: take every BYSETPOS case of
conformance/cases.ndjson, run the dtical adapter over them twice -- once with
RRULE_DTICAL_ITER=iterator (the published column) and once with `chain` -- at
each case's own corpus limit with a 10-second per-case deadline, and bucket
each run as agrees-with-expect / disagrees / timed-out.

"Agrees" is exact list equality with `expect`, the same blunt test score.py
uses; a rival reading counts as a disagreement here, because the question is
whether the two traversals answer differently, not whether either is right.
"""
import argparse, collections, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CASES = os.path.join(REPO, "conformance", "cases.ndjson")
ADAPTER = os.path.join(REPO, "conformance", "adapters", "perl", "dtical_adapter.pl")


def load_setpos(path):
    out = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            if "BYSETPOS" in case["rrule"].upper():
                out.append(case)
    return out


def run(cases, traversal, case_timeout, wall):
    """Feed every case to one traversal of the adapter; return id -> reply."""
    env = dict(os.environ)
    env["TZ"] = "UTC"                      # rule 69
    env["RRULE_DTICAL_ITER"] = traversal
    env["RRULE_CASE_TIMEOUT"] = str(case_timeout)
    stdin = "".join(json.dumps(c) + "\n" for c in cases)
    proc = subprocess.run(["perl", ADAPTER], input=stdin, capture_output=True,
                          text=True, timeout=wall, env=env, cwd=REPO)
    if proc.returncode != 0:
        sys.exit("adapter exited %d: %s" % (proc.returncode, proc.stderr[-2000:]))
    replies = {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line:
            r = json.loads(line)
            replies[r["id"]] = r
    return replies


def bucket(case, reply):
    if reply is None:
        return "missing"
    if "error" in reply:
        return "timeout"
    return "agrees" if reply.get("occurrences") == case["expect"] else "disagrees"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=CASES)
    ap.add_argument("--case-timeout", type=int, default=10)
    ap.add_argument("--wall", type=float, default=7200)
    ap.add_argument("--out")
    a = ap.parse_args(argv)

    cases = load_setpos(a.cases)
    print("%d BYSETPOS cases" % len(cases))

    runs = {}
    for traversal in ("iterator", "chain"):
        print("running %s ..." % traversal, flush=True)
        runs[traversal] = run(cases, traversal, a.case_timeout, a.wall)

    counts = {t: collections.Counter() for t in runs}
    differ = []
    for case in cases:
        answers = {}
        for t, replies in runs.items():
            reply = replies.get(case["id"])
            counts[t][bucket(case, reply)] += 1
            answers[t] = ("error" if reply is None or "error" in reply
                          else tuple(reply["occurrences"]))
        if answers["iterator"] != answers["chain"]:
            differ.append({
                "id": case["id"], "rrule": case["rrule"],
                "dtstart": case["dtstart"], "limit": case["limit"],
                "expect": case["expect"],
                "iterator": runs["iterator"].get(case["id"]),
                "chain": runs["chain"].get(case["id"]),
            })

    for t in ("iterator", "chain"):
        print("%-9s %s" % (t, dict(counts[t])))
    both = [r for r in differ if r["iterator"] and "error" not in r["iterator"]
            and r["chain"] and "error" not in r["chain"]]
    print("differ between traversals: %d of %d" % (len(differ), len(cases)))
    print("  of which both traversals actually answered: %d" % len(both))
    print("  of which one side hit the %ds deadline:      %d"
          % (a.case_timeout, len(differ) - len(both)))

    if a.out:
        sys.path.insert(0, os.path.join(REPO, "tools"))
        try:
            from corpus_id import compute            # rule 77
            cid = compute()["cases_id"]
        except Exception as exc:                     # pragma: no cover
            cid = "unavailable: %s" % exc
        with open(a.out, "w") as fh:
            json.dump({
                "finding": "046 (derivation saved retroactively, rule 79)",
                "cases_id": cid, "cases_file": os.path.relpath(a.cases, REPO),
                "n_setpos_cases": len(cases), "case_timeout_s": a.case_timeout,
                "counts": {t: dict(counts[t]) for t in counts},
                "n_differ": len(differ),
                "n_differ_both_answered": len(both),
                "n_differ_one_side_timed_out": len(differ) - len(both),
                "load_dependence_warning": (
                    "The timeout bucket depends on machine load, so n_differ and"
                    " the agrees/disagrees split are not stable across runs."
                    " n_differ_both_answered is the part that does not depend on"
                    " an answer arriving in time."),
                "differ": differ,
            }, fh, indent=1, sort_keys=True)
        print("wrote %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

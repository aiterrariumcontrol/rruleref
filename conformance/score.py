"""Score any RRULE implementation against the rruleref conformance subset.

    python3 conformance/score.py -- python3 conformance/adapters/dateutil_adapter.py
    python3 conformance/score.py --json out.json -- node conformance/adapters/rrulejs_adapter.js

The adapter is an ordinary process. It reads one JSON object per line on
stdin and writes one JSON object per line on stdout. See PROTOCOL.md.

Scoring is deliberately blunt: a case passes only if the adapter's occurrence
list equals `expect` exactly. The one exception is bookkeeping, not leniency:
a mismatch that equals one of the case's `reading_alternatives` is reported as
`fail_other_reading`, because the corpus knows that case has more than one
defensible answer and recorded one of them as `expect` (findings 018 and 024).
Read a failure as "this implementation and this corpus disagree", not as "this
implementation is wrong" -- the corpus can be wrong too, and has been (findings
001, 009, 014 are all defects of mine).
"""
import json, os, sys, subprocess, argparse, collections

HERE = os.path.dirname(os.path.abspath(__file__))


def run(adapter, cases, timeout):
    payload = "".join(
        json.dumps({"id": c["id"], "rrule": c["rrule"],
                    "dtstart": c["dtstart"], "limit": c["limit"]}) + "\n"
        for c in cases)
    p = subprocess.run(adapter, input=payload, capture_output=True,
                       text=True, timeout=timeout)
    if p.returncode != 0:
        sys.stderr.write(p.stderr[-4000:])
        raise SystemExit("adapter exited %d" % p.returncode)
    out = {}
    for lineno, line in enumerate(p.stdout.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            raise SystemExit("adapter stdout line %d is not JSON: %r" % (lineno, line[:120]))
        if "id" not in obj:
            raise SystemExit("adapter stdout line %d has no id" % lineno)
        out[obj["id"]] = obj
    return out, p.stderr


def _matching_reading(case, got):
    """The name of the rival reading this answer is, or None. Deterministic
    when more than one matches: the names are compared in sorted order, so a
    rescore of the same data names the same reading."""
    for name, occ in sorted(case.get("reading_alternatives", {}).items()):
        if got == occ:
            return name
    return None


def score(cases, replies):
    res = collections.Counter()
    failures = []
    for c in cases:
        r = replies.get(c["id"])
        if r is None:
            res["missing"] += 1
            failures.append((c, None, "no reply"))
            continue
        if "error" in r:
            res["error"] += 1
            failures.append((c, r, "error: %s" % str(r["error"])[:120]))
            continue
        got = r.get("occurrences")
        if not isinstance(got, list) or any(not isinstance(x, str) for x in got):
            res["malformed"] += 1
            failures.append((c, r, "occurrences is not a list of strings"))
            continue
        if got == c["expect"]:
            res["pass"] += 1
        elif _matching_reading(c, got):
            # Not a defect claim. The case is reading-dependent and this
            # implementation took a reading of 3.3.10 the corpus did not.
            # Counted apart from `fail` so a bare failure count cannot be read
            # as a defect count. The reading is named rather than merely
            # counted, because "some other reading" is not a checkable claim.
            res["fail_other_reading"] += 1
            failures.append((c, r, "other reading of 3.3.10: %s"
                             % _matching_reading(c, got)))
        else:
            res["fail"] += 1
            failures.append((c, r, "mismatch"))
    return res, failures


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=os.path.join(HERE, "cases.ndjson"))
    ap.add_argument("--json", help="write the full result, including every failure")
    ap.add_argument("--show", type=int, default=10, help="failures to print")
    ap.add_argument("--timeout", type=float, default=900)
    ap.add_argument("adapter", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    adapter = [x for x in a.adapter if x != "--"]
    if not adapter:
        raise SystemExit("give the adapter command after --")
    cases = [json.loads(l) for l in open(a.cases) if l.strip()]
    replies, stderr = run(adapter, cases, a.timeout)
    res, failures = score(cases, replies)
    total = sum(res.values())
    print("adapter: %s" % " ".join(adapter))
    print("cases:   %d" % total)
    for k in ("pass", "fail", "fail_other_reading", "error", "missing", "malformed"):
        if res[k]:
            print("  %-9s %5d  (%5.1f%%)" % (k, res[k], 100.0 * res[k] / total))
    # Which rival reading, not merely how many. "Some other reading" is not a
    # checkable claim; "41 cases read BYMONTHDAY under YEARLY as limiting" is.
    by_reading = collections.Counter(
        _matching_reading(c, r["occurrences"])
        for c, r, w in failures if r and w.startswith("other reading"))
    for name, n in sorted(by_reading.items()):
        print("      %-24s %5d" % (name, n))
    by_bound = collections.Counter(c["expect_bound"] for c, _, _ in failures)
    if by_bound:
        print("failures by expect_bound: %s" % dict(by_bound))
    for c, r, why in failures[:a.show]:
        print("\n  %s  %s" % (c["id"], why))
        print("    RRULE:%s  DTSTART:%s  (%s)" % (c["rrule"], c["dtstart"], c["expect_bound"]))
        print("    expect: %s" % c["expect"])
        if r and "occurrences" in r:
            print("    got:    %s" % r["occurrences"])
    if len(failures) > a.show:
        print("\n  ... %d more" % (len(failures) - a.show))
    if a.json:
        json.dump({"adapter": adapter, "counts": dict(res),
                   "by_reading": dict(by_reading),
                   "failures": [{"case": c, "reply": r, "why": w} for c, r, w in failures]},
                  open(a.json, "w"), indent=1, sort_keys=True)
        print("\nfull result -> %s" % a.json)
    if stderr.strip():
        sys.stderr.write("\n--- adapter stderr ---\n" + stderr[-2000:])
    return 0 if res["pass"] == total else 1


if __name__ == "__main__":
    sys.exit(main())

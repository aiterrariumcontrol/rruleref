"""Ask whether two score runs failed on the SAME CASES, not merely the same number.

    python3 conformance/compare_residuals.py A.json B.json
    python3 conformance/compare_residuals.py A.json B.json --bucket fail --show 20

Both arguments are `--json` outputs of score.py. The tool reports, per bucket,
how many ids each run has, how many they share, and which ids belong to only
one of them.

Why this exists: finding 056 published "7 ical4j cases and 7 dmfs cases" as if
that were two facts. It was one -- the same seven ids, which is what identified
the shared Java adapter rather than either library as the cause (057). Two runs
with an equal residual count are the case where the count is least informative
and the membership most informative, so an EQUAL COUNT with DIFFERENT MEMBERS
is called out here as the loudest line in the report.

The same operation answers two different questions, depending on what the two
files are:

  two implementations   -- do they fail on the same cases (shared cause) or on
                           disjoint ones (independent defects)?
  one implementation twice -- does the residual reproduce? A count that
                           reproduces while the membership does not is a
                           load-dependent or nondeterministic adapter, which
                           the dtical 20s alarm is (findings 047, and rule 55).

Bucket names come from score.py's `bucket` field. Files written before that
field existed are classified from the `why` prose instead, so already-published
findings/data/*.json can still be compared.
"""
import json, sys, argparse

# `why` prefixes, for result files written before score.py recorded `bucket`.
LEGACY = [("no reply", "missing"),
          ("error:", "error"),
          ("occurrences is not a list", "malformed"),
          ("other reading of 3.3.10:", "fail_other_reading"),
          ("proper prefix of expect", "fail_prefix"),
          ("proper prefix of other reading:", "fail_other_reading_prefix"),
          ("mismatch", "fail")]

ORDER = ["fail", "fail_other_reading", "fail_prefix",
         "fail_other_reading_prefix", "error", "missing", "malformed"]


def bucket_of(f):
    if "bucket" in f:
        return f["bucket"]
    why = f.get("why", "")
    for prefix, name in LEGACY:
        if why.startswith(prefix):
            return name
    return "unclassified"


def load(path):
    """path -> {bucket: {id: why}}. Missing `failures` is an error, not an
    empty result: a file without it is not a score.py --json output."""
    d = json.load(open(path))
    if "failures" not in d:
        raise SystemExit("%s has no `failures` list -- not a score.py --json output"
                         % path)
    out = {}
    for f in d["failures"]:
        out.setdefault(bucket_of(f), {})[f["case"]["id"]] = f.get("why", "")
    return d, out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("left")
    ap.add_argument("right")
    ap.add_argument("--bucket", action="append",
                    help="restrict to this bucket; repeatable (default: all)")
    ap.add_argument("--show", type=int, default=10,
                    help="ids to list per side (default 10, 0 for none)")
    a = ap.parse_args(argv)

    dl, L = load(a.left)
    dr, R = load(a.right)
    print("left:  %s\n       %s" % (a.left, " ".join(dl.get("adapter", ["?"]))))
    print("right: %s\n       %s" % (a.right, " ".join(dr.get("adapter", ["?"]))))

    buckets = [b for b in ORDER if b in L or b in R]
    buckets += sorted((set(L) | set(R)) - set(ORDER))
    if a.bucket:
        buckets = [b for b in buckets if b in a.bucket]
        for b in a.bucket:
            if b not in buckets:
                print("\n%s: absent from both files" % b)

    alarms = 0
    for b in buckets:
        li, ri = set(L.get(b, {})), set(R.get(b, {}))
        both, only_l, only_r = li & ri, li - ri, ri - li
        print("\n=== %s ===" % b)
        print("  left %d   right %d   shared %d   left-only %d   right-only %d"
              % (len(li), len(ri), len(both), len(only_l), len(only_r)))
        if li == ri:
            print("  SAME CASES.")
        elif len(li) == len(ri):
            # The line this tool exists for.
            alarms += 1
            print("  ** EQUAL COUNT, DIFFERENT MEMBERS -- %d ids differ. The count"
                  % len(only_l))
            print("     is a coincidence here; do not report it as one fact. **")
        else:
            print("  Different counts and different members.")
        for label, ids in (("left-only", only_l), ("right-only", only_r)):
            if ids and a.show:
                src = L if label == "left-only" else R
                for i in sorted(ids)[:a.show]:
                    print("    %-9s %s  %s" % (label, i, src[b][i][:70]))
                if len(ids) > a.show:
                    print("    %-9s ... %d more" % (label, len(ids) - a.show))
    # Exit 1 means "the two files differ somewhere", so this is usable in a
    # check. The equal-count alarm is reported, not given its own exit code:
    # it is a reading hazard, not a failure.
    if alarms:
        print("\n%d bucket(s) with an equal count and different members." % alarms)
    same = all(set(L.get(b, {})) == set(R.get(b, {})) for b in buckets)
    print("\n%s" % ("identical residuals in every bucket compared"
                    if same else "residuals differ"))
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())

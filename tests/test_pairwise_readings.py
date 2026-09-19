"""pairwise_readings.py: what must NOT count as two lineages agreeing.

Finding 060. The tool's value is entirely in its exclusions -- a port agreeing
with its parent, two libraries both returning nothing, an answer the corpus
already records -- and in the `*BOUND` flag, which marks an agreement that was
never tested past the case's own COUNT. Each exclusion is pinned here, because
each one silently inflates the result if it regresses.
"""
import sys, os, json, tempfile, io, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "conformance"))
import pairwise_readings as P

FAILURES = []


def check(name, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + name + (("  -- " + extra) if extra and not cond else ""))
    if not cond:
        FAILURES.append(name)


def write(tmp, name, rows, limit=8, bound="count"):
    """A minimal score.py --json output. `rows` is (id, bucket, occurrences)."""
    p = os.path.join(tmp, name)
    json.dump({"adapter": [name], "counts": {},
               "failures": [{"case": {"id": i, "rrule": "FREQ=DAILY",
                                      "dtstart": "20260101T090000",
                                      "limit": limit, "expect_bound": bound,
                                      "expect": ["E"]},
                             "reply": {"id": i, "occurrences": occ},
                             "why": "mismatch", "bucket": b}
                            for i, b, occ in rows]},
              open(p, "w"))
    return "%s=%s" % (name.split(".")[0], p)


def run(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        groups = P.main(list(argv))
    return groups, buf.getvalue()


def main():
    print("pairwise_readings.py")
    tmp = tempfile.mkdtemp()
    A = ["a1", "a2", "a3"]          # a short answer: does not reach limit 8
    B = ["b1", "b2", "b3"]

    # Two lineages on the same answer: the thing the tool is for.
    ical4j = write(tmp, "ical4j.json", [("c1", "fail", A)])
    dmfs = write(tmp, "dmfs.json", [("c1", "fail", A)])
    groups, out = run("--show", "0", "--run", ical4j, "--run", dmfs)
    check("two lineages on one answer is reported", len(groups) == 1, out)
    check("both lineages are named",
          groups and groups[0]["lineages"] == ["dmfs", "ical4j"], out)

    # A port agreeing with its parent is one observation and a copy (003).
    rrulejs = write(tmp, "rrulejs.json", [("c1", "fail", A)])
    rust = write(tmp, "rust.json", [("c1", "fail", A)])
    groups, out = run("--show", "0", "--run", rrulejs, "--run", rust)
    check("agreement within one lineage is not reported", groups == [], out)

    # Two libraries that both return nothing share no reading of anything.
    e1 = write(tmp, "ical4j.json", [("c1", "fail", [])])
    e2 = write(tmp, "dmfs.json", [("c1", "fail", [])])
    groups, out = run("--show", "0", "--run", e1, "--run", e2)
    check("agreement on the empty list is not a group", groups == [], out)
    check("agreement on the empty list is still counted separately",
          "EMPTY list (not counted): 1" in out, out)

    # Only `fail` means "the corpus records this nowhere". A bucket that names
    # a recorded reading, or a prefix of one, must not be mistaken for it.
    for bucket in ("fail_other_reading", "fail_prefix",
                   "fail_other_reading_prefix", "error", "missing"):
        x = write(tmp, "ical4j.json", [("c1", bucket, A)])
        y = write(tmp, "dmfs.json", [("c1", bucket, A)])
        groups, out = run("--show", "0", "--run", x, "--run", y)
        check("bucket %s is not an unrecorded reading" % bucket, groups == [], out)

    # Different answers on the same case are a disagreement, not a reading.
    x = write(tmp, "ical4j.json", [("c1", "fail", A)])
    y = write(tmp, "dmfs.json", [("c1", "fail", B)])
    groups, out = run("--show", "0", "--run", x, "--run", y)
    check("two lineages failing differently is not a group", groups == [], out)

    # The 060 rule. An answer that runs to the case's own COUNT was never
    # tested past it; a shorter one was free to diverge and did not.
    long_ = ["o%d" % i for i in range(8)]
    x = write(tmp, "ical4j.json", [("c1", "fail", long_)])
    y = write(tmp, "dmfs.json", [("c1", "fail", long_)])
    groups, out = run("--show", "1", "--run", x, "--run", y)
    check("an answer reaching the COUNT bound is flagged *BOUND",
          groups and groups[0]["bound_limited"] and "*BOUND" in out, out)
    x = write(tmp, "ical4j.json", [("c1", "fail", A)])
    y = write(tmp, "dmfs.json", [("c1", "fail", A)])
    groups, out = run("--show", "1", "--run", x, "--run", y)
    check("an answer short of the bound is not flagged",
          groups and not groups[0]["bound_limited"] and "*BOUND" not in out, out)
    # A case bounded by a horizon rather than a COUNT has no such bound.
    x = write(tmp, "ical4j.json", [("c1", "fail", long_)], bound="horizon")
    y = write(tmp, "dmfs.json", [("c1", "fail", long_)], bound="horizon")
    groups, out = run("--show", "0", "--run", x, "--run", y)
    check("a horizon-bounded case is not flagged *BOUND",
          groups and not groups[0]["bound_limited"], out)

    # An unlabelled adapter cannot be counted, because the question is lineage.
    try:
        run("--show", "0", "--run", ical4j, "--run", "mystery=" + tmp + "/dmfs.json")
        check("an adapter with no lineage is rejected", False, "it was accepted")
    except SystemExit:
        check("an adapter with no lineage is rejected", True)

    print("\n%d checks failed" % len(FAILURES) if FAILURES else "\nall checks passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())

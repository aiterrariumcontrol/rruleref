"""score.py's buckets, and the one asymmetry in the corpus that makes the
prefix bucket necessary.

Finding 057. The corpus applies its declared `horizon_days` to every `expect`
list and to only some of its `reading_alternatives`, so an adapter that clips at
the declared horizon cannot match those alternatives by equality. The scorer
must report that as a prefix rather than as a mismatch, and must not report an
empty answer as a prefix of everything.
"""
import sys, os, json, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "conformance"))
import score as S

FAILURES = []


def check(name, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + name + (("  -- " + extra) if extra and not cond else ""))
    if not cond:
        FAILURES.append(name)


CASE = {"id": "x", "rrule": "FREQ=YEARLY", "dtstart": "20260101T090000",
        "limit": 4, "expect_bound": "count",
        "expect": ["a", "b", "c", "d"],
        "reading_alternatives": {"dtstart_fill": ["a", "b", "x", "y"]}}


def bucket(got):
    res, _ = S.score([CASE], {"x": {"id": "x", "occurrences": got}})
    return [k for k in res if res[k]][0]


def main():
    print("score.py buckets")
    check("exact expect is a pass", bucket(["a", "b", "c", "d"]) == "pass")
    check("exact alternative is fail_other_reading",
          bucket(["a", "b", "x", "y"]) == "fail_other_reading")
    check("proper prefix of expect is fail_prefix",
          bucket(["a", "b", "c"]) == "fail_prefix")
    check("proper prefix of an alternative is fail_other_reading_prefix",
          bucket(["a", "b", "x"]) == "fail_other_reading_prefix")
    check("a prefix of both is charged to expect",
          bucket(["a", "b"]) == "fail_prefix")
    check("the empty answer is a mismatch, not a prefix of everything",
          bucket([]) == "fail", bucket([]))
    check("a longer answer is a mismatch, not a prefix",
          bucket(["a", "b", "c", "d", "e"]) == "fail")
    check("a divergent answer of the same length is a mismatch",
          bucket(["a", "b", "z", "d"]) == "fail")

    print("\nthe corpus horizon, applied to one side only")
    meta = json.load(open(os.path.join(ROOT, "corpus", "corroborated.json")))["meta"]
    h = meta["horizon_days"]
    # Asserted as an agreement, not as a literal. The number is meant to
    # change -- it has been 10958 and is now 109500 -- and pinning it here only
    # made this check fail the next time it did. What must hold is rule 66's
    # single definition: the committed corpus and the expander's default are
    # the same horizon.
    sys.path.insert(0, os.path.join(ROOT, "src"))
    import naive
    check("corpus horizon agrees with naive.HORIZON_DAYS",
          h == naive.HORIZON_DAYS, "%s vs %s" % (h, naive.HORIZON_DAYS))

    def when(s):
        return (datetime.datetime.strptime(s[:15], "%Y%m%dT%H%M%S") if "T" in s
                else datetime.datetime.strptime(s[:8], "%Y%m%d"))

    cases = [json.loads(l) for l in
             open(os.path.join(ROOT, "conformance", "cases.ndjson")) if l.strip()]
    past_expect, alts, past_alt = 0, 0, 0
    for c in cases:
        end = when(c["dtstart"]) + datetime.timedelta(days=h)
        if any(when(x) > end for x in c["expect"]):
            past_expect += 1
        for _, v in sorted(c.get("reading_alternatives", {}).items()):
            alts += 1
            if any(when(x) > end for x in v):
                past_alt += 1
    check("no expect list runs past the declared horizon", past_expect == 0,
          str(past_expect))
    # Not pinned to a number: the corpus grows. Pinned to the *asymmetry*, which
    # is the thing finding 057 is about. If this ever reaches zero the prefix
    # bucket has nothing left to catch on the Java rows and RESULTS.md should say so.
    print("       %d of %d reading_alternatives lists run past it" % (past_alt, alts))
    check("the asymmetry is still there", past_alt > 0)

    print("\n%d checks failed" % len(FAILURES) if FAILURES else "\nall checks passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())

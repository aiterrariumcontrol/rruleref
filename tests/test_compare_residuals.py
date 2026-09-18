"""compare_residuals.py: equal counts must not be reported as equal sets.

Rule 54, learned the hard way in finding 056 and corrected in 057. The case
the tool exists for -- two runs with the same residual count and different
members -- does not occur in any published pair, so it is constructed here.
Also pins the fallback that lets the tool read result files written before
score.py recorded an explicit `bucket`.
"""
import sys, os, json, tempfile, io, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "conformance"))
import compare_residuals as C

FAILURES = []


def check(name, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + name + (("  -- " + extra) if extra and not cond else ""))
    if not cond:
        FAILURES.append(name)


def write(tmp, name, failures, adapter="adapter"):
    """A minimal score.py --json output. `failures` is a list of
    (id, why, bucket); bucket None omits the field, as old files do."""
    p = os.path.join(tmp, name)
    json.dump({"adapter": [adapter], "counts": {},
               "failures": [dict({"case": {"id": i}, "reply": {}, "why": w},
                                 **({"bucket": b} if b else {}))
                            for i, w, b in failures]},
              open(p, "w"))
    return p


def run(*argv):
    """(exit code, stdout)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = C.main(list(argv))
    return rc, buf.getvalue()


def main():
    print("compare_residuals.py")
    tmp = tempfile.mkdtemp()

    # The whole point. Same count, disjoint members.
    a = write(tmp, "a.json", [("id1", "mismatch", "fail"), ("id2", "mismatch", "fail")])
    b = write(tmp, "b.json", [("id3", "mismatch", "fail"), ("id4", "mismatch", "fail")])
    rc, out = run(a, b)
    check("equal count with different members is flagged",
          "EQUAL COUNT, DIFFERENT MEMBERS" in out, out)
    check("equal count with different members is not 'SAME CASES'",
          "SAME CASES" not in out, out)
    check("equal count with different members exits nonzero", rc == 1)
    check("both sides' ids are listed", "id1" in out and "id3" in out, out)

    # Identical sets, reported in the opposite order, are identical.
    c = write(tmp, "c.json", [("id2", "mismatch", "fail"), ("id1", "mismatch", "fail")])
    rc, out = run(a, c)
    check("the same ids in a different order are SAME CASES", "SAME CASES" in out, out)
    check("identical residuals exit zero", rc == 0)
    check("identical residuals are not flagged",
          "EQUAL COUNT, DIFFERENT" not in out, out)

    # Differing counts must not borrow the equal-count alarm.
    d = write(tmp, "d.json", [("id1", "mismatch", "fail")])
    rc, out = run(a, d)
    check("unequal counts are not flagged as a coincidence",
          "EQUAL COUNT" not in out and "Different counts" in out, out)
    check("a shared id is counted as shared", "shared 1" in out, out)

    # Equal counts in DIFFERENT buckets are not equal counts. id1 fails on the
    # left and errors on the right: one id each, but nothing to compare.
    e = write(tmp, "e.json", [("id1", "error: boom", "error")])
    rc, out = run(d, e)
    check("buckets are compared separately, not totals",
          "EQUAL COUNT" not in out, out)

    # Files written before score.py recorded `bucket`.
    legacy = write(tmp, "legacy.json",
                   [("id1", "mismatch", None),
                    ("id5", "error: boom", None),
                    ("id6", "other reading of 3.3.10: dtstart_fill", None),
                    ("id7", "proper prefix of expect (2 of 4)", None),
                    ("id8", "proper prefix of other reading: dtstart_fill (2 of 4)", None),
                    ("id9", "no reply", None)])
    _, buckets = C.load(legacy)
    for want, ident in (("fail", "id1"), ("error", "id5"),
                        ("fail_other_reading", "id6"), ("fail_prefix", "id7"),
                        ("fail_other_reading_prefix", "id8"), ("missing", "id9")):
        check("legacy `why` classifies %s" % want,
              ident in buckets.get(want, {}), str(buckets))
    check("nothing lands in `unclassified`", "unclassified" not in buckets, str(buckets))

    # An explicit bucket wins over the prose, so a future `why` wording change
    # cannot silently reclassify a fresh file.
    odd = write(tmp, "odd.json", [("id1", "mismatch", "error")])
    _, buckets = C.load(odd)
    check("an explicit bucket overrides the prose", "id1" in buckets.get("error", {}),
          str(buckets))

    # A file that is not a score output must not read as an empty residual,
    # which would silently compare as "identical".
    notascore = os.path.join(tmp, "no.json")
    json.dump({"about": "a curated finding file"}, open(notascore, "w"))
    try:
        C.load(notascore)
        check("a file with no `failures` is rejected", False, "it was accepted")
    except SystemExit:
        check("a file with no `failures` is rejected", True)

    print("\n%d checks failed" % len(FAILURES) if FAILURES else "\nall checks passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())

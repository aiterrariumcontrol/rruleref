"""conformance/reading_past_bound.py: does a reading match survive the bound?

The verdicts decide whether score.py's `fail_other_reading` excuse is real, so
each one is pinned here on synthetic data rather than on an adapter run.
"""
import os, sys, json, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "conformance"))
import reading_past_bound as R  # noqa: E402

FAILED = []


def check(name, cond, detail=""):
    print("%-58s %s" % (name, "ok" if cond else "FAIL"))
    if not cond:
        FAILED.append("%s %s" % (name, detail))


# A case whose `expect` runs to 3 and whose rival reading differs from the
# first occurrence on. `long_readings` is what the reading extends to at the
# probe limit.
CASE = {"id": "x", "rrule": "FREQ=DAILY", "dtstart": "20260101T000000",
        "expect": ["a", "b", "c"],
        "reading_alternatives": {"alt": ["A", "b", "c"]}}
LONG = {"alt": ["A", "b", "c", "d", "e"]}

check("no answer is n/a", R.judge(CASE, LONG, None, 5)[0] == "n/a")
check("answer matching expect is n/a", R.judge(CASE, LONG, ["a", "b", "c", "d", "e"], 5)[0] == "n/a")
check("following the reading to the limit holds",
      R.judge(CASE, LONG, ["A", "b", "c", "d", "e"], 5)[:2] == ("holds", "alt"))
check("leaving the reading after the bound breaks",
      R.judge(CASE, LONG, ["A", "b", "c", "Z", "e"], 5)[:3] == ("breaks", "alt", 3))
check("stopping early while agreeing is truncated",
      R.judge(CASE, LONG, ["A", "b", "c", "d"], 5)[:3] == ("truncated", "alt", 4))
check("an answer short of the bound cannot claim the reading",
      R.judge(CASE, LONG, ["A", "b"], 5)[0] == "n/a")
check("a reading that stops differing further out is merged",
      R.judge(CASE, {}, ["A", "b", "c", "d", "e"], 5)[:2] == ("merged", "alt"))
check("the reference running out first is not a break",
      R.judge(CASE, {"alt": ["A", "b", "c"]}, ["A", "b", "c", "d", "e"], 5)[:3]
      == ("reference_exhausted", "alt", 3))
check("an empty reading is never matched",
      R.judge(dict(CASE, reading_alternatives={"alt": []}), {"alt": []},
              [], 5)[0] == "n/a")
check("an empty reading does not swallow a normal answer",
      R.judge(dict(CASE, reading_alternatives={"alt": []}), {"alt": []},
              ["a", "b", "c"], 5)[0] == "n/a")
check("first_difference finds the index", R._first_difference("abXd", "abYd") == 2)
check("first_difference on a prefix returns the shorter length",
      R._first_difference("ab", "abcd") == 2)

# extend() must refuse a case that no longer regenerates: the whole report is
# a comparison against regenerated readings, so silent drift would be fatal.
bad = dict(CASE, dtstart="20260101T000000", rrule="FREQ=DAILY",
           expect=["nonsense"], reading_alternatives={"alt": ["x"]})
try:
    R.extend(bad, 5)
    check("extend refuses a case that does not regenerate", False, "no SystemExit")
except SystemExit:
    check("extend refuses a case that does not regenerate", True)

# Round trip through the real corpus: every alternative-carrying case must
# regenerate byte for byte at its own length (this is what extend() asserts).
cases = R.alt_cases(R.DEFAULT_CASES)
check("corpus has alternative-carrying cases", len(cases) > 0, str(len(cases)))
ok = True
for c in cases:
    try:
        long, readings = R.extend(c, 25)
    except SystemExit as e:
        ok = False
        print("   ", c["id"], e)
        break
    if len(long) < len(c["expect"]):
        print("   ", c["id"], "shorter than its own corpus row")
        ok = False
        break
check("every alternative-carrying case regenerates and extends", ok)

# The probe must ask for more than the corpus row does, or it tests nothing.
with tempfile.NamedTemporaryFile("w+", suffix=".ndjson", delete=False) as f:
    path = f.name
R.main(["--emit-probe", "-o", path, "--limit", "25"])
rows = [json.loads(l) for l in open(path)]
os.unlink(path)
check("probe covers every alternative-carrying case", len(rows) == len(cases))
check("probe asks for the longer limit", all(r["limit"] == 25 for r in rows))
by_id = {c["id"]: c for c in cases}
check("probe carries the case's own rule and DTSTART unchanged",
      all(r["rrule"] == by_id[r["id"]]["rrule"]
          and r["dtstart"] == by_id[r["id"]]["dtstart"] for r in rows))

print()
if FAILED:
    print("%d FAILED" % len(FAILED))
    for f in FAILED:
        print("  " + f)
    sys.exit(1)
print("all checks passed")

"""Checks for src/grammar.py and src/enumerate_branches.py.

The claim under test is "the corpus takes every branch of RFC 5545 3.3.10's
RECUR ABNF". That is only worth anything if the grammar really is the RFC's,
if a branch id means the same thing to the enumerator and to the classifier,
and if the cases are rules the spec permits. Each of those is checked here.
"""
import sys, os, json
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import env
env.add_dateutil_to_path()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from datetime import datetime
import grammar
import enumerate_branches as eb
import validity

FAIL = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        FAIL.append(msg)


def eq(got, want, msg):
    check(got == want, "%s (got %r)" % (msg, got))


# -- the grammar is the RFC's ------------------------------------------------
src = grammar.source()
eq(list(src)[0], "recur", "first extracted production is `recur`")
eq(list(src)[-1], "setposday", "last extracted production is `setposday`")
eq(len(src), 28, "28 productions extracted from 3.3.10")
eq(src["freq"],
   '"SECONDLY" / "MINUTELY" / "HOURLY" / "DAILY" / "WEEKLY" / "MONTHLY" / "YEARLY"',
   "freq alternation transcribed from the RFC, not from memory")
eq(src["weekday"], '"SU" / "MO" / "TU" / "WE" / "TH" / "FR" / "SA"',
   "weekday alternation")
eq(src["plus"], '"+"', "plus is an explicit literal in the ABNF")
check("enddate" in src and "/" in src["enddate"],
      "enddate is an alternation (date / date-time)")

g = grammar.grammar()
check(g["freq"][0] == "alt" and len(g["freq"][1]) == 7, "freq parses to 7 alternatives")
check(grammar._is_leaf_rule(g["seconds"]), "`seconds = 1*2DIGIT` is a numeric leaf")
check(not grammar._is_leaf_rule(g["weekdaynum"]), "weekdaynum is not a leaf")

# -- features ----------------------------------------------------------------
feats = grammar.features()
eq(len(feats), len(set(feats)), "feature ids are unique")
eq(len(feats), 79, "79 branches in the RECUR grammar")
for f in ["FREQ|freq|SECONDLY", "recur|recur-rule-part|COUNT",
          "UNTIL|enddate|date", "BYDAY|weekdaynum/0/0/0/0|plus",
          "WKST|weekday|SA", "recur|recur/1|repeat=0"]:
    check(f in feats, "feature present: " + f)
check("BYDAY|weekday|MO" in feats and "WKST|weekday|MO" in feats,
      "`weekday` reached from BYDAY and from WKST are distinct obligations")
check(not any(f.startswith("seconds") for f in feats),
      "the 1-vs-2-digit branch of a numeric leaf is not a feature")

# -- classify ----------------------------------------------------------------
eq(sorted(grammar.classify("FREQ=DAILY")),
   ["FREQ|freq|DAILY", "recur|recur-rule-part|FREQ", "recur|recur/1|repeat=0"],
   "a one-part rule takes exactly three branches")
check("recur|recur/1|repeat=1+" in grammar.classify("FREQ=DAILY;INTERVAL=2"),
      "a two-part rule takes the recur repetition")
check("BYDAY|weekdaynum/0/0/0/0|plus" in grammar.classify("FREQ=MONTHLY;BYDAY=+1MO"),
      "an explicit + on BYDAY is a distinct branch from no sign")
check("BYDAY|weekdaynum/0|absent" in grammar.classify("FREQ=MONTHLY;BYDAY=MO"),
      "a bare weekday takes the ordwk-absent branch")
check("BYSECOND|byseclist/1|repeat=0" in grammar.classify("FREQ=MINUTELY;BYSECOND=1"),
      "a one-element list is the repeat=0 branch")
check("BYSECOND|byseclist/1|repeat=1+" in grammar.classify("FREQ=MINUTELY;BYSECOND=1,2"),
      "a two-element list is the repeat=1+ branch")
eq(grammar.classify("FREQ=DAILY;UNTIL=20260305") ^
   grammar.classify("FREQ=DAILY;UNTIL=20260305T090000"),
   {"UNTIL|enddate|date", "UNTIL|enddate|date-time"},
   "the two UNTIL value types differ in exactly one branch")
for bad in ["FREQ=BOGUS", "FREQ=DAILY;", "FREQ=DAILY;BYDAY=8MO,",
            "FREQ=DAILY;COUNT=x", "FREQ=DAILY;BYDAY=MONDAY"]:
    try:
        grammar.classify(bad)
        check(False, "rejected as ungrammatical: " + bad)
    except ValueError:
        check(True, "rejected as ungrammatical: " + bad)

# The ABNF's own constraints live in its *comments* -- "The FREQ rule part is
# REQUIRED, but MUST NOT occur more than once", the value ranges, UNTIL vs
# COUNT -- and the extractor drops comments by design. So the grammar accepts
# strings the spec forbids, and src/validity.py is what rejects them. Branch
# coverage and validity are separate measurements; neither substitutes for the
# other, and this pins that they line up.
for permitted_but_invalid in ["BYDAY=MO", "FREQ=DAILY;FREQ=WEEKLY",
                              "FREQ=DAILY;BYDAY=MO;BYDAY=TU",
                              "FREQ=DAILY;COUNT=2;UNTIL=20260305T090000",
                              "FREQ=DAILY;BYMONTH=13"]:
    try:
        grammar.classify(permitted_but_invalid)
        ok = True
    except ValueError:
        ok = False
    check(ok, "grammar accepts (comments are not enforced): "
              + permitted_but_invalid)
    check(bool(validity.violations(permitted_but_invalid)),
          "validity rejects it: " + permitted_but_invalid)


# -- the enumerated cases ----------------------------------------------------
cases = eb.cases()
eq(len(cases), len(feats), "one case per branch")
covered = set()
for feature, rule, ds in cases:
    taken = grammar.classify(rule)
    check(feature in taken, "case for %s takes it" % feature)
    covered |= taken
    v = validity.violations(rule)
    check(not v, "case for %s is valid per 3.3.10: %s" % (feature, rule))
    check(isinstance(ds, datetime), "case for %s has a DTSTART" % feature)
eq(sorted(set(feats) - covered), [], "the case set covers every branch")

# A case whose branch never changes the answer is coverage on paper: UNTIL and
# COUNT must actually bound the eight occurrences the corpus records.
from naive import expand
for feature in ["recur|recur-rule-part|UNTIL", "recur|recur-rule-part|COUNT"]:
    _, rule, ds = [c for c in cases if c[0] == feature][0]
    check(len(expand(rule, ds, limit=8)) < 8,
          "%s terminates inside the recorded window: %s" % (feature, rule))

# -- the corpus actually reaches them ----------------------------------------
cov_path = os.path.join(os.path.dirname(__file__), "..", "corpus",
                        "grammar-coverage.json")
if os.path.exists(cov_path):
    cov = json.load(open(cov_path))
    eq(cov["meta"]["branches"], len(feats), "coverage file counts every branch")
    eq(cov["uncovered"], [], "no branch is unexercised by the corpus")
    # Branches needing a DATE-valued DTSTART used to be reported here, because
    # the main corpus is entirely DATE-TIME. They are now covered conformantly
    # by corpus/date-value-type.json (finding 011), so this must be empty --
    # and every one of them must actually appear in that file.
    eq(cov["covered_nonconformantly"], [],
       "no branch is covered only non-conformantly")
    dv = json.load(open(os.path.join(os.path.dirname(__file__), "..", "corpus",
                                     "date-value-type.json")))
    check(eb.NEEDS_DATE_DTSTART <= set(dv["branches"]),
          "the DATE-valued branches are covered by the DATE corpus")
    corpus = json.load(open(os.path.join(os.path.dirname(__file__), "..",
                                         "corpus", "corroborated.json")))
    check(all("branches" in c for c in corpus["cases"]),
          "every corroborated case records the branches it takes")
    sample = corpus["cases"][0]
    eq(sorted(grammar.classify(sample["rrule"])), sample["branches"],
       "a recorded branch list reproduces from the rule alone")
else:
    print("skip corpus checks: corpus/grammar-coverage.json not built yet")

print("\n%s" % ("all checks passed" if not FAIL else "%d FAILED" % len(FAIL)))
sys.exit(1 if FAIL else 0)

"""RFC 5545 recurrence with a DATE-valued DTSTART.

Three things are pinned here:

1. that the RFC sentences `src/datevalue.py` acts on are really in the RFC --
   quoted text is checked against the hashed copy, never trusted from memory;
2. that `corpus/date-value-type.json` reproduces exactly from the generator,
   so the file is a record and not a hand-edited artifact;
3. what `python-dateutil` 2.9.0 currently *does* with a DATE-valued DTSTART.
   Point 3 is deliberately a pin on today's behaviour: if a future release
   starts honouring 3.3.10's MUST-ignore, this test fails loudly instead of the
   corpus quietly changing meaning. Same pattern as tests/test_byweekno.py.

Run: PYTHONPATH=... python3 tests/test_date_value_type.py
"""

import json
import os
import re
import sys
from datetime import date, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import env
env.add_dateutil_to_path()

import datevalue
import datevalue_cases
from dateutil.rrule import rrulestr

RFC = env.rfc_path("5545")
CORPUS = os.path.join(ROOT, "corpus", "date-value-type.json")

checks = 0
fails = []


def check(cond, what):
    global checks
    checks += 1
    if not cond:
        fails.append(what)


def rfc_says(sentence):
    """True if `sentence` appears in the RFC, ignoring its line wrapping."""
    with open(RFC) as f:
        text = re.sub(r"\s+", " ", f.read())
    return re.sub(r"\s+", " ", sentence).strip() in text


# 1. The spec text this module depends on.
check(rfc_says("The BYSECOND, BYMINUTE and BYHOUR rule parts MUST NOT be "
               "specified when the associated \"DTSTART\" property has a DATE "
               "value type."), "MUST NOT sentence in RFC")
check(rfc_says("These rule parts MUST be ignored in RECUR value that violate "
               "the above requirement"), "MUST-ignore remedy in RFC")
check(rfc_says("The value of the UNTIL rule part MUST have the same value "
               "type as the \"DTSTART\" property."), "UNTIL value-type MUST")
# The remedy is new in RFC 5545; RFC 2445 has no such sentence. That is why
# implementations with a 2445 lineage expand the time parts.
with open(env.rfc_path("2445")) as f:
    old = re.sub(r"\s+", " ", f.read())
check("MUST be ignored in RECUR value" not in old, "remedy absent from RFC 2445")
check("BYSECOND, BYMINUTE and BYHOUR rule parts MUST NOT" not in old,
      "prohibition absent from RFC 2445")

# 2. The reduction itself.
check(datevalue.ignored_parts("FREQ=DAILY;BYHOUR=9") == ["BYHOUR"], "ignored BYHOUR")
check(datevalue.ignored_parts("FREQ=DAILY;BYSECOND=1;BYMINUTE=2;BYHOUR=3")
      == ["BYSECOND", "BYMINUTE", "BYHOUR"], "ignored all three")
check(datevalue.ignored_parts("FREQ=DAILY;BYMONTHDAY=3") == [], "nothing to ignore")
check(datevalue.reduce_rule("RRULE:FREQ=DAILY;BYHOUR=9;COUNT=2")
      == "FREQ=DAILY;COUNT=2", "reduce keeps order and drops the prefix")
check(datevalue.reduce_rule("FREQ=DAILY;BYDAY=MO") == "FREQ=DAILY;BYDAY=MO",
      "reduce is identity on a conformant rule")

# The parts are ignored, not applied: an all-day event with BYHOUR=9,17 is one
# occurrence a day, not two.
occ = datevalue.expand("FREQ=DAILY;BYHOUR=9,17", date(2026, 1, 5), limit=4)
check(occ == [date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7),
              date(2026, 1, 8)], "BYHOUR ignored, one occurrence per day")
check(all(isinstance(x, date) and not isinstance(x, datetime) for x in occ),
      "expansion yields dates, not datetimes")

# A DATE-valued UNTIL is required here and is inclusive (3.3.10: "bounds the
# recurrence rule in an inclusive manner").
check(datevalue.expand("FREQ=DAILY;UNTIL=20260108", date(2026, 1, 5))
      == [date(2026, 1, d) for d in (5, 6, 7, 8)], "DATE UNTIL is inclusive")

# Refusals, rather than invented answers.
for rule in ("FREQ=HOURLY", "FREQ=MINUTELY", "FREQ=SECONDLY",
             "FREQ=DAILY;UNTIL=20260108T000000Z"):
    try:
        datevalue.expand(rule, date(2026, 1, 5))
        check(False, "should refuse %s" % rule)
    except datevalue.UndefinedForDateValue:
        check(True, "refuses %s" % rule)
try:
    datevalue.expand("FREQ=DAILY", datetime(2026, 1, 5))
    check(False, "should reject a datetime dtstart")
except TypeError:
    check(True, "rejects a datetime dtstart")

# 3. The corpus file reproduces, and says what it claims.
doc = json.load(open(CORPUS))
for case in doc["cases"]:
    ds, _kind = datevalue.parse_dtstart(case["dtstart"])
    got = [datevalue.fmt(x) for x in
           datevalue.expand(case["rrule"], ds, limit=len(case["expect"]) or 8)]
    check(got[:len(case["expect"])] == case["expect"],
          "reproduces %s @ %s" % (case["rrule"], case["dtstart"]))
    check(bool(case["corroborated_by"]),
          "corroborated %s" % case["rrule"])
    check(all(len(x) == 8 and x.isdigit() for x in case["expect"]),
          "dates only in %s" % case["rrule"])
    check(case["conformant_as_written"] == (not case["ignored_parts"]),
          "conformance flag agrees with ignored_parts for %s" % case["rrule"])
check(len(doc["cases"]) == len(datevalue_cases.CASES), "case count matches source")
check("UNTIL|enddate|date" in doc["branches"],
      "the DATE-valued UNTIL grammar branch is covered here")

# 4. Today's python-dateutil behaviour, pinned.
with_parts = [c for c in doc["cases"] if c["ignored_parts"]]
check(len(with_parts) == 6, "six cases carry parts that must be ignored")
for case in with_parts:
    check(not case["observed_midnight_only"]["python-dateutil-2.9.0"],
          "dateutil still applies the time parts for %s" % case["rrule"])
# and the direct probe, so this does not depend on the corpus file at all
out = list(rrulestr("FREQ=DAILY;BYHOUR=9,17;COUNT=4", dtstart=date(2026, 1, 5)))
check([x.hour for x in out] == [9, 17, 9, 17],
      "dateutil expands BYHOUR under a date dtstart (pinned 2026-09-06)")

print("%d checks, %d failed" % (checks, len(fails)))
for f in fails:
    print("  FAIL:", f)
sys.exit(1 if fails else 0)

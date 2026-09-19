#!/usr/bin/env python3
"""Finding 059: which yearly period owns a week that straddles 1 January.

Pins four things:
  1. the flag is inert where the question does not arise -- no FREQ other than
     YEARLY, no rule without BYWEEKNO, and no output change at INTERVAL=1
     without BYSETPOS, which is why the reading stayed invisible for 58
     findings;
  2. the INTERVAL=2 demonstration that the calendar-year reading fires twice
     in one selected period and not at all in the next;
  3. that the reading reproduces, exactly, the lists two independent lineages
     return on the four cases finding 058 could not attribute;
  4. that the corpus records the reading under the names 059 claims.
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import env
env.add_dateutil_to_path()
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

from naive import expand  # noqa: E402

fails = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name)
    if not ok:
        fails.append((name, got, want))


def run(rule, ds, n, wy=False):
    return [x.strftime("%Y%m%dT%H%M%S")
            for x in expand(rule, datetime.strptime(ds, "%Y%m%dT%H%M%S"),
                            limit=n, week_based_year=wy)]


print("1. the flag is inert where the question does not arise")
for rule, ds in (("FREQ=YEARLY;BYMONTH=3;BYMONTHDAY=1", "20260301T090000"),
                 ("FREQ=MONTHLY;BYDAY=1MO", "20260105T090000"),
                 ("FREQ=WEEKLY;BYDAY=TU,TH", "20260106T090000"),
                 ("FREQ=DAILY;INTERVAL=3", "20260101T090000")):
    check("inert: " + rule, run(rule, ds, 12, wy=True), run(rule, ds, 12))

# The readings must coincide whenever every consecutive year is expanded and
# no BYSETPOS is selecting from a period: a misattributed day is still emitted,
# just under a neighbouring period. 31 occurrences over four decades.
check("INTERVAL=1 without BYSETPOS is identical",
      run("FREQ=YEARLY;BYWEEKNO=1;BYDAY=MO", "19900101T090000", 31, wy=True),
      run("FREQ=YEARLY;BYWEEKNO=1;BYDAY=MO", "19900101T090000", 31))

print("2. INTERVAL=2 separates them, and the calendar reading double-fires")
RULE2 = "FREQ=YEARLY;INTERVAL=2;BYWEEKNO=1;BYDAY=MO"
cal = run(RULE2, "20240101T090000", 5)
wby = run(RULE2, "20240101T090000", 5, wy=True)
check("calendar reading emits two occurrences inside the 2024 period",
      cal[:3], ["20240101T090000", "20241230T090000", "20280103T090000"])
check("and therefore none for the 2026 period",
      [x for x in cal if x.startswith("2026")], [])
check("week-based reading emits exactly one per selected week-year",
      wby[:5], ["20240101T090000", "20251229T090000", "20280103T090000",
                "20291231T090000", "20311229T090000"])
# Five occurrences under the calendar reading cover only four distinct
# calendar years, because two of them share 2024; under the week-based
# reading five occurrences are five distinct week-years.
check("calendar: 5 occurrences, 4 distinct years",
      (len(cal), len(set(x[:4] for x in cal))), (5, 4))
check("week-based: 5 occurrences, 5 distinct years",
      (len(wby), len(set(x[:4] for x in wby))), (5, 5))

print("3. it reproduces what two independent lineages return")
DATA = os.path.join(ROOT, "findings", "data", "058-universal-residual.json")
cases = {c["id"]: c for c in json.load(open(DATA))["cases"]}
# id -> (compose with dtstart_fill?, the lineages that agree on it)
EXPECTED = {
    "1b491afa4ef0": (False, ["ical4j", "dmfs"]),
    "36fa68873abe": (False, ["libical", "ical4j"]),
    "39497d02ae1e": (True, ["libical", "ical4j"]),
    "cd5d1f7e7232": (True, ["ical4j", "dmfs"]),
}
sys.path.insert(0, os.path.join(ROOT, "src"))
from build_corpus import _dtstart_fill_rewrite  # noqa: E402

for cid, (fill, lineages) in sorted(EXPECTED.items()):
    c = cases[cid]
    ds = datetime.strptime(c["dtstart"], "%Y%m%dT%H%M%S")
    rule = _dtstart_fill_rewrite(c["rrule"], ds) if fill else c["rrule"]
    check("%s == %s" % (cid, "+".join(lineages)),
          run(rule, c["dtstart"], c["limit"], wy=True),
          c["answers"][lineages[0]]["occurrences"])
    # The point of the composition: on these two, neither half alone does it.
    if fill:
        check("%s needs both halves (week_based_year alone differs)" % cid,
              run(c["rrule"], c["dtstart"], c["limit"], wy=True)
              != c["answers"][lineages[0]]["occurrences"], True)
        check("%s needs both halves (dtstart_fill alone differs)" % cid,
              run(rule, c["dtstart"], c["limit"])
              != c["answers"][lineages[0]]["occurrences"], True)

print("4. the corpus records the reading")
corr = json.load(open(os.path.join(ROOT, "corpus", "corroborated.json")))
names = set()
for c in corr["cases"]:
    names.update(c.get("reading_alternatives", {}))
check("week_based_year is recorded", "week_based_year" in names, True)
check("the composed reading is recorded",
      "week_based_year+dtstart_fill" in names, True)

print()
if fails:
    print("%d check(s) failed" % len(fails))
    for name, got, want in fails:
        print("  %s\n    got  %r\n    want %r" % (name, got, want))
    sys.exit(1)
print("all checks passed")

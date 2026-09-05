"""Rule-validity checks against RFC 5545 3.3.10.

Includes the case the Human raised on 2026-09-05: 13 corroborated cases
combined FREQ=YEARLY, BYWEEKNO and a numeric BYDAY, which 3.3.10 prohibits.
Implementations accepted them and agreed, and agreement was being read as
conformance evidence.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import validity

FAILURES = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (("  " + extra) if extra else ""))
    if not cond:
        FAILURES.append(name)


INVALID = [
    ("FREQ=YEARLY;BYDAY=-1SU;BYWEEKNO=53;WKST=WE", "byday-numeric-byweekno"),
    ("FREQ=WEEKLY;BYDAY=2MO", "byday-numeric-freq"),
    ("FREQ=DAILY;BYDAY=-1FR", "byday-numeric-freq"),
    ("FREQ=WEEKLY;BYMONTHDAY=15", "bymonthday-weekly"),
    ("FREQ=MONTHLY;BYYEARDAY=60", "byyearday-freq"),
    ("FREQ=MONTHLY;BYWEEKNO=3", "byweekno-freq"),
    ("FREQ=MONTHLY;BYSETPOS=1", "bysetpos-needs-byxxx"),
    ("FREQ=MONTHLY;BYMONTHDAY=32", "value-range"),
    ("FREQ=YEARLY;BYWEEKNO=54", "value-range"),
    ("FREQ=DAILY;COUNT=3;UNTIL=20260101T000000Z", "count-until-exclusive"),
    ("BYDAY=MO", "freq-required"),
]

VALID = [
    "FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=-1",   # RFC 3.3.10 example
    "FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=-2",   # RFC 3.8.5.3 example
    "FREQ=YEARLY;BYDAY=-1SU;BYMONTH=10",               # numeric BYDAY, no BYWEEKNO
    "FREQ=YEARLY;BYWEEKNO=20;BYDAY=MO",                # non-numeric BYDAY is fine
    "FREQ=WEEKLY;BYDAY=TU,TH;BYSETPOS=2",
    "FREQ=DAILY;INTERVAL=2;COUNT=10",
]


def main():
    for rule, expected in INVALID:
        vs = validity.violations(rule)
        ids = [v["rule"] for v in vs]
        check("invalid: " + rule, expected in ids, str(ids))
    for rule in VALID:
        vs = validity.violations(rule)
        check("valid:   " + rule, not vs, str([v["rule"] for v in vs]))

    # Every rule appearing in a shipped corpus file must carry a rule_valid flag
    # that agrees with a fresh evaluation.
    here = os.path.join(os.path.dirname(__file__), "..", "corpus")
    for name in ("corroborated.json", "disputed.json"):
        path = os.path.join(here, name)
        if not os.path.exists(path):
            continue
        cases = json.load(open(path))["cases"]
        mismatched = [c["rrule"] for c in cases
                      if c.get("rule_valid") != validity.is_valid(c["rrule"])]
        check("%s flags agree with validity.py" % name, not mismatched,
              str(mismatched[:3]))

    print("\n%d failure(s)" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())

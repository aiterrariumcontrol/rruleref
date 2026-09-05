"""Known-answer tests from the examples in RFC 5545 sec. 3.8.5.3.

These are the one source of expected values that comes from neither expander,
so they check the corpus method itself rather than just the two implementations
against each other. Run: python3 tests/rfc_examples.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from datetime import datetime
from naive import expand

CASES = [
    # (rule, dtstart, expected, note)
    ("FREQ=DAILY;INTERVAL=2;COUNT=3", datetime(1997, 9, 2, 9),
     ["19970902T090000", "19970904T090000", "19970906T090000"], ""),
    ("FREQ=MONTHLY;BYDAY=-1SU;COUNT=3", datetime(1997, 9, 28, 9),
     ["19970928T090000", "19971026T090000", "19971130T090000"], "last Sunday"),
    ("FREQ=MONTHLY;BYMONTHDAY=-3;COUNT=3", datetime(1997, 9, 28, 9),
     ["19970928T090000", "19971029T090000", "19971128T090000"], "3rd-from-last day"),
    ("FREQ=YEARLY;BYDAY=20MO;COUNT=3", datetime(1997, 5, 19, 9),
     ["19970519T090000", "19980518T090000", "19990517T090000"], "20th Monday of the year"),
    ("FREQ=YEARLY;BYWEEKNO=20;BYDAY=MO;COUNT=3", datetime(1997, 5, 12, 9),
     ["19970512T090000", "19980511T090000", "19990517T090000"], "Monday of week 20"),
    ("FREQ=YEARLY;INTERVAL=2;BYMONTH=1;BYDAY=SU;BYHOUR=8,9;BYMINUTE=30",
     datetime(1997, 1, 5, 8, 30),
     ["19970105T083000", "19970105T093000", "19970112T083000"], "expansion at two levels"),

    # The WKST pair the RFC uses to show that WKST changes the answer. Both
    # implementations reproduce both lines exactly.
    ("FREQ=WEEKLY;INTERVAL=2;COUNT=4;BYDAY=TU,SU;WKST=MO", datetime(1997, 8, 5, 9),
     ["19970805T090000", "19970810T090000", "19970819T090000", "19970824T090000"],
     "RFC: August 5,10,19,24"),
    ("FREQ=WEEKLY;INTERVAL=2;COUNT=4;BYDAY=TU,SU;WKST=SU", datetime(1997, 8, 5, 9),
     ["19970805T090000", "19970817T090000", "19970819T090000", "19970831T090000"],
     "RFC: August 5,17,19,31 -- same rule, different WKST"),

    # CORRECTION 2026-09-05. This slot previously held a fabricated case: the
    # BYSETPOS=-1 rule, which RFC 5545 gives only in the prose of sec. 3.3.10
    # with no expected output, paired with expected values invented around the
    # sec. 3.8.5.3 example's dates -- and then reported as an "erratum in the
    # RFC". There is no erratum. The RFC's worked example uses BYSETPOS=-2 and
    # its printed results are correct. Both real examples are below.
    ("FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=-2;COUNT=6", datetime(1997, 9, 29, 9),
     ["19970929T090000", "19971030T090000", "19971127T090000", "19971230T090000",
      "19980129T090000", "19980226T090000"],
     "second-to-last weekday of the month"),
    ("FREQ=MONTHLY;COUNT=3;BYDAY=TU,WE,TH;BYSETPOS=3", datetime(1997, 9, 4, 9),
     ["19970904T090000", "19971007T090000", "19971106T090000"],
     "third TU/WE/TH into the month"),
]


def main():
    bad = 0
    for rule, ds, expected, note in CASES:
        got = [d.strftime("%Y%m%dT%H%M%S") for d in expand(rule, ds)[:len(expected)]]
        ok = got == expected
        bad += not ok
        print("%s %s%s" % ("PASS" if ok else "FAIL", rule,
                           ("   # " + note) if note else ""))
        if not ok:
            print("     expected", expected)
            print("     got     ", got)
    print("\n%d/%d pass" % (len(CASES) - bad, len(CASES)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

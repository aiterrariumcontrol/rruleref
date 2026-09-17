"""Systematic cases: at least one per RFC 5545 3.3.10 table cell.

The random generator in differ.gen never emitted a sub-daily FREQ and never
emitted BYHOUR/BYMINUTE/BYSECOND at all, so 36 of the table's 57 permitted
cells were empty and nothing in the corpus said so. These cases are chosen by
the cell they occupy, not by a seed, so the corpus's coverage becomes a
statement that a test can check.

Each case carries the cell it was built for. A cell may hold more than one
case: where 3.3.10 permits a negative value, the cell is emitted twice, once
per sign -- see NEG_VALUES. DTSTART is anchored near the
rule's own matching region: the naive expander is a brute force over candidate
instants, and FREQ=SECONDLY;BYMONTH=3 starting in January costs five million
iterations to reach its first occurrence.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from datetime import datetime
import coverage

SUB = ("SECONDLY", "MINUTELY", "HOURLY")

# A DTSTART that already satisfies the limiting parts, so the brute force does
# not have to walk months of seconds to find occurrence one.
ANCHOR = {
    "BYMONTH": datetime(2026, 3, 2, 9, 0, 0),
    "BYWEEKNO": datetime(2026, 5, 11, 9, 0, 0),
    "BYYEARDAY": datetime(2026, 3, 1, 9, 0, 0),   # day 60 of 2026
    "BYMONTHDAY": datetime(2026, 3, 15, 9, 0, 0),
    "BYDAY": datetime(2026, 3, 2, 9, 0, 0),       # a Monday
    "BYHOUR": datetime(2026, 3, 2, 9, 0, 0),
    "BYMINUTE": datetime(2026, 3, 2, 9, 30, 0),
    "BYSECOND": datetime(2026, 3, 2, 9, 30, 0),
    "BYSETPOS": datetime(2026, 3, 2, 9, 0, 0),
}

VALUES = {
    "BYMONTH": "3",
    "BYWEEKNO": "20",
    "BYYEARDAY": "60",
    "BYMONTHDAY": "15",
    "BYHOUR": "9,18",
    "BYMINUTE": "0,30",
    "BYSECOND": "0,15",
}

# 3.3.10 lets BYMONTHDAY and BYYEARDAY count from the end of the period as well
# as from the start, and the two directions are *different code paths* in real
# implementations. Covering a table cell with a positive value only says the
# cell was visited; it says nothing about the sign. Finding 049 is exactly that
# blind spot: ical4j resolves a negative day correctly when the rule part
# expands and compares it raw when the same rule part limits, so the whole
# Limit column was scored by cases that could not see the defect.
NEG_VALUES = {
    "BYMONTHDAY": "-1",
    "BYYEARDAY": "-1",
}

#: Anchored at the end of the period the negative value names, for ANCHOR's
#: reason: the brute force must not walk a year of seconds to reach occurrence
#: one.
NEG_ANCHOR = {
    "BYMONTHDAY": datetime(2026, 3, 31, 9, 0, 0),
    "BYYEARDAY": datetime(2026, 12, 31, 9, 0, 0),
}


def _byday(freq, branch):
    """The BYDAY rule for a cell, plus the companion parts its branch needs."""
    if freq == "MONTHLY":
        if branch == coverage.NOTE1[0]:
            return "BYDAY=MO;BYMONTHDAY=15,16,17"
        return "BYDAY=2MO"          # special expand for MONTHLY
    if freq == "YEARLY":
        if branch == coverage.NOTE2[0]:
            return "BYDAY=MO;BYMONTHDAY=15,16,17"
        if branch == coverage.NOTE2[1]:
            # numeric BYDAY is forbidden here by 3.3.10; plain weekday only
            return "BYDAY=MO;BYWEEKNO=20"
        if branch == coverage.NOTE2[2]:
            return "BYDAY=MO;BYMONTH=3"
        return "BYDAY=-1MO"         # special expand for YEARLY
    if freq == "WEEKLY":
        return "BYDAY=MO,WE"
    return "BYDAY=MO"               # Limit, for the sub-daily and DAILY rows


def _parts(part, freq, branch):
    if part == "BYDAY":
        return _byday(freq, branch)
    if part == "BYSETPOS":
        # 3.3.10: BYSETPOS "MUST only be used in conjunction with another
        # BYxxx rule part". The companion is chosen so the set it selects from
        # has more than one member, or BYSETPOS would be a no-op.
        comp = "BYSECOND=0,15,30" if freq in SUB else "BYDAY=MO,WE,FR"
        return "BYSETPOS=-1;" + comp
    return part + "=" + VALUES[part]


def cases():
    """[(cell, rrule, dtstart)] -- every permitted cell, deterministic.

    One rule per cell, plus a second rule for the cells whose rule part accepts
    a negative value. The negative variant is filed under the *same* cell: it
    is not a new cell of 3.3.10's table, it is the other sign of one that was
    already there.
    """
    out = []
    for part, freq, branch in coverage.cells():
        rule = "FREQ=%s;%s" % (freq, _parts(part, freq, branch))
        out.append(((part, freq, branch), rule, ANCHOR[part]))
        if part in NEG_VALUES:
            neg = "FREQ=%s;%s=%s" % (freq, part, NEG_VALUES[part])
            out.append(((part, freq, branch), neg, NEG_ANCHOR[part]))
    return out


if __name__ == "__main__":
    for cell, rule, ds in cases():
        print("%-52s %s  DTSTART=%s" % ("/".join(cell), rule, ds))

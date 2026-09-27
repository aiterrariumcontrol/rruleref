"""Apply libical BYWEEKNO patches A and/or B to a pristine icalrecur.c.

Every anchor must occur exactly once in the source, or the patcher refuses.
Rule 116's discipline: a patch that silently matches zero or two places is a
predictor fitted to nothing.
"""
import os, sys, pathlib

SRC = pathlib.Path(os.environ.get("LIBICAL_SRC", "/home/agent/terrarium/scratch/libical")) / "src/libical/icalrecur.c"

# ---- A: weeks_in_year() hardcodes the ISO (Monday) week start; the numbering
#         it is compared against comes from ICU with FIRST_DAY_OF_WEEK=WKST.
A = [
 ("""/** Calculate ISO weeks per year
   https://en.wikipedia.org/wiki/ISO_week_date#Weeks_per_year */
static int weeks_in_year(int year)
{
    /* Long years occur when year starts on Thu or leap year starts on Wed */
    int dow = icaltime_day_of_week(icaltime_from_day_of_year(1, year));
    int is_long = (dow == 5 || (dow == 4 && icaltime_is_leap_year(year)));

    return (52 + is_long);
}""",
  """/** Calculate weeks per year for a given week start
   https://en.wikipedia.org/wiki/ISO_week_date#Weeks_per_year */
static int weeks_in_year_ws(int year, int week_start)
{
    /* Long years occur when the year starts on the 4th day of the week,
       or a leap year starts on the 3rd.  For week_start == MO this is the
       ISO rule (Thu, or Wed in a leap year). */
    int dow = icaltime_day_of_week(icaltime_from_day_of_year(1, year));
    int nd = dow - (week_start - 1);
    int is_long;

    if (nd <= 0) {
        nd += 7;
    }
    is_long = (nd == 4 || (nd == 3 && icaltime_is_leap_year(year)));

    return (52 + is_long);
}

static int weeks_in_year_iso(int year)
{
    return weeks_in_year_ws(year, (int)ICAL_MONDAY_WEEKDAY);
}

#define weeks_in_year(y) weeks_in_year_ws((y), (int)impl->rule->week_start)"""),
 # the non-ICU get_week_number is compiled out here but must stay consistent
 ("""    int dow, week;

    _unused(impl);
""",
  """    int dow, week;
"""),
]

# ---- B: the BYWEEKNO+BYDAY period length.  expand_by_day() takes last_day as
#         a COUNT of days starting at doy_offset + 1; the week-numbering year is
#         exactly 7 * weeks_in_year days long.
B = [
 ("""                last_day = (7 * weeks_in_year(year)) - doy_offset - 1;""",
  """                last_day = (short)(7 * weeks_in_year(year));"""),
]


def apply(text, pairs, label):
    for old, new in pairs:
        n = text.count(old)
        if n != 1:
            sys.exit("patch %s: anchor occurs %d times, refusing:\n%s" % (label, n, old[:80]))
        text = text.replace(old, new)
    return text


def main():
    want = set(sys.argv[1:]) or {"A", "B"}
    if not want <= {"A", "B"}:
        sys.exit("usage: patch112.py [A] [B]   (no args = both)")
    text = SRC.read_text()
    if "weeks_in_year_ws" in text or "weeks_in_year_iso" in text:
        sys.exit("source is already patched; git checkout it first")
    if "A" in want:
        text = apply(text, A, "A")
    if "B" in want:
        text = apply(text, B, "B")
    # unused-static warnings are errors in this build for weeks_in_year_iso
    if "A" in want:
        text = text.replace("static int weeks_in_year_iso(int year)\n{\n    return weeks_in_year_ws(year, (int)ICAL_MONDAY_WEEKDAY);\n}\n\n", "")
    SRC.write_text(text)
    print("applied:", "".join(sorted(want)))


main()

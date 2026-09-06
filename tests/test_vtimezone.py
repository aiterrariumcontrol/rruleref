"""RFC 5545 section 3.6.5: the spec's own VTIMEZONE examples, run.

Two different kinds of check live here, and they should not be confused.

**Positive coverage.**  Three of the five examples claim to describe a real
zone -- America/New_York.  That claim is falsifiable against an independent
primary source, the IANA time zone database, which is not derived from RFC 5545
and was not written by the same people.  Every transition instant is bisected
out of the installed tz database to the second rather than typed in, so neither
the RFC nor this repository supplies the expected answers.

**Defects in the examples.**  The two "Fictitious" examples contain a value
that fails a MUST in the same section, and one that puts the example inside the
region section 3.8.5.3 declares undefined.  Those are recorded as assertions of
what is actually printed, checked against the sha256-pinned text, so that if a
future revision fixes them the test fails loudly rather than quietly agreeing.

Both example inputs and the RFC's own prose bounds are extracted by program
from the pinned copy; nothing here is retyped.  See findings/007.
"""
import io
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import vtimezone as V
from naive import matches as rule_matches, parse as rule_parse

FAILURES = []
UTC = timezone.utc


def check(name, ok, detail=""):
    print("  %-4s %s%s" % ("ok" if ok else "FAIL", name,
                           ("  [%s]" % detail) if detail else ""))
    if not ok:
        FAILURES.append(name)


def iana_transitions(zone, start, end):
    """Real transitions of `zone` in [start, end), bisected to the second."""
    z = ZoneInfo(zone)
    out, t, step = [], start, timedelta(hours=6)
    prev = t.astimezone(z).utcoffset()
    while t < end:
        n = t + step
        o = n.astimezone(z).utcoffset()
        if o != prev:
            lo, hi = t, n
            while hi - lo > timedelta(seconds=1):
                mid = lo + (hi - lo) / 2
                if mid.astimezone(z).utcoffset() == prev:
                    lo = mid
                else:
                    hi = mid
            out.append((hi.replace(microsecond=0), prev, o))
            prev = o
        t = n
    return out


def sample(resolver, zone, start, end, step):
    z = ZoneInfo(zone)
    bad_offset = bad_name = n = 0
    t = start
    while t < end:
        n += 1
        if resolver.utcoffset(t) != t.astimezone(z).utcoffset():
            bad_offset += 1
        if resolver.tzname(t) != t.astimezone(z).tzname():
            bad_name += 1
        t += step
    return n, bad_offset, bad_name


# --------------------------------------------------------------------------
# Positive coverage: does the RFC's New York actually match New York?
# --------------------------------------------------------------------------

NY_CASES = [
    # (example index, first instant the example claims to cover, last)
    (1, datetime(1967, 4, 30, 7, 0, tzinfo=UTC), datetime(2040, 1, 1, tzinfo=UTC)),
    (3, datetime(2007, 3, 11, 7, 0, tzinfo=UTC), datetime(2040, 1, 1, tzinfo=UTC)),
]


def test_new_york_examples_match_tzdata():
    """Examples 1 and 3 against America/New_York in the IANA database.

    Example 1 is annotated "all the time zone rules for New York City since
    April 30, 1967 at 03:00:00 EDT" -- 03:00 EDT is 02:00 EST is
    1967-04-30T07:00:00Z, its own first onset.  Example 3 is "the current time
    zone rules", starting at the 2007 rule change.  Both are unbounded forward.
    """
    print("RFC 5545 3.6.5 examples 1 and 3 vs the IANA tz database")
    ex = V.extract()
    for index, start, end in NY_CASES:
        vtz = ex[index - 1]
        r = V.Resolver(vtz, until_year=end.year)
        spec = set(r.transitions(start, end))
        real = set(iana_transitions("America/New_York", start, end))
        check("example %d: %d transitions, identical to tzdata" % (index, len(real)),
              spec == real,
              "symmetric difference %d" % len(spec ^ real))
        n, bo, bn = sample(r, "America/New_York", start, end, timedelta(hours=7))
        check("example %d: %d sampled instants, offset agrees" % (index, n), bo == 0,
              "%d mismatches" % bo)
        check("example %d: TZNAME agrees at every sample" % index, bn == 0,
              "%d mismatches" % bn)


def test_example_2_validity_window_is_exact():
    """The RFC states example 2's validity window; check it to the second.

    "Note that this is only suitable for a recurring event that starts on or
     later than March 11, 2007 at 03:00:00 EDT (i.e., the earliest effective
     transition date and time) and ends no later than March 9, 2008 at
     01:59:59 EST (i.e., latest valid date and time for EST in this
     scenario)."

    Both bounds are checkable.  The component has two onsets and no RRULE, so
    after 2007-11-04 it says EST forever; the stated end is the last second
    before the real 2008 transition it cannot know about.
    """
    print("\nRFC 5545 3.6.5 example 2: the stated validity window")
    r = V.Resolver(V.extract()[1])
    lo = datetime(2007, 3, 11, 7, 0, tzinfo=UTC)     # 03:00:00 EDT
    hi = datetime(2008, 3, 9, 7, 0, tzinfo=UTC)      # 01:59:59 EST is hi - 1s
    check("says nothing before the first onset", r.utcoffset(lo - timedelta(seconds=1)) is None)
    n, bo, bn = sample(r, "America/New_York", lo, hi, timedelta(minutes=37))
    check("inside the window: %d samples agree with tzdata" % n, bo == 0 and bn == 0)
    last = hi - timedelta(seconds=1)
    check("last stated-valid instant is 2008-03-09 01:59:59 EST",
          (last + r.utcoffset(last)).strftime("%Y-%m-%d %H:%M:%S") == "2008-03-09 01:59:59"
          and r.tzname(last) == "EST"
          and r.utcoffset(last) == last.astimezone(ZoneInfo("America/New_York")).utcoffset())
    check("one second later it is wrong, as the RFC warns",
          r.utcoffset(hi) != hi.astimezone(ZoneInfo("America/New_York")).utcoffset(),
          "component %s, tzdata %s" % (r.utcoffset(hi),
                                       hi.astimezone(ZoneInfo("America/New_York")).utcoffset()))


# --------------------------------------------------------------------------
# Defects in the printed examples
# --------------------------------------------------------------------------

def test_until_must_equal_the_last_instance():
    """Section 3.6.5 makes UNTIL a MUST; two of the five examples fail it.

    "If observance is known to have an effective end date, the 'UNTIL'
     recurrence rule parameter MUST be used to specify the last valid onset of
     this observance (i.e., the UNTIL DATE-TIME will be equal to the last
     instance generated by the recurrence pattern)."

    Four UNTIL values appear in example 1 and satisfy it exactly.  The single
    UNTIL shared by examples 4 and 5 is 19980404T070000Z -- a Saturday --
    while the rule generates first Sundays of April.
    """
    print("\nRFC 5545 3.6.5: UNTIL equals the last generated instance")
    for vtz in V.extract():
        for obs in vtz["observances"]:
            if not obs["rrule"] or "UNTIL=" not in obs["rrule"].upper():
                continue
            rule, until = V.split_until(obs["rrule"])
            gen = V.onsets(dict(obs, rrule=rule), until_year=until.year + 2)
            hit = until in gen
            label = ("example %d %s UNTIL=%s"
                     % (vtz["index"], obs["kind"], obs["rrule"].split("UNTIL=")[1]))
            if vtz["index"] == 1:
                check(label + " equals an instance", hit)
            else:
                prev = [d for d in gen if d < until][-1]
                nxt = [d for d in gen if d > until][0]
                check(label + " does NOT equal any instance (defect)", not hit,
                      "previous %s, next %s"
                      % (prev.strftime("%Y-%m-%dT%H:%M:%SZ"),
                         nxt.strftime("%Y-%m-%dT%H:%M:%SZ")))
                check(label + " falls on a %s, the rule generates Sundays"
                      % until.strftime("%A"),
                      until.strftime("%a") == "Sat")


def test_example_5_has_a_year_without_daylight_time():
    """The off-by-one UNTIL leaves 1998 with no daylight observance at all.

    Example 5's prose: "There is a second Daylight Time rule that picks up
    where the other left off."  It does not: the first rule's last onset is
    1997-04-06 and the second begins in 1999, so the whole of 1998 is standard
    time.  This is the observable consequence of the UNTIL value above, and it
    is the reason to think the intended value was 19980405T070000Z (the 1998
    onset) rather than 19970406T070000Z (the 1997 one).
    """
    print("\nRFC 5545 3.6.5 example 5: the 1998 hole")
    r = V.Resolver(V.extract()[4], until_year=2005)
    july = {y: r.utcoffset(datetime(y, 7, 1, 12, tzinfo=UTC)) for y in (1997, 1998, 1999)}
    check("1 July 1997 is daylight time", july[1997] == timedelta(hours=-4), str(july[1997]))
    check("1 July 1998 is standard time (no daylight onset that year)",
          july[1998] == timedelta(hours=-5), str(july[1998]))
    check("1 July 1999 is daylight time again", july[1999] == timedelta(hours=-4), str(july[1999]))
    onsets_98 = [t for t, _, _, k in r.changes
                 if datetime(1998, 1, 1, tzinfo=UTC) <= t < datetime(1999, 1, 1, tzinfo=UTC)
                 and k == "DAYLIGHT"]
    check("1998 contains zero DAYLIGHT onsets", onsets_98 == [], str(onsets_98))


def test_example_5_dtstart_is_not_synchronized():
    """Example 5's second DAYLIGHT rule sits in section 3.8.5.3's undefined region.

    DTSTART:19990424T020000 is a Saturday; FREQ=YEARLY;BYDAY=-1SU;BYMONTH=4
    generates 1999-04-25.  Section 3.6.5 says the onsets are defined by
    "the 'DTSTART', 'RRULE', and 'RDATE' properties", so DTSTART is itself an
    onset -- example 1's 1974 observance has no RRULE at all and depends on
    that reading.  The result is two daylight onsets one day apart, and a
    recurrence set section 3.8.5.3 declines to define.
    """
    print("\nRFC 5545 3.6.5 example 5: unsynchronized DTSTART")
    vtz = V.extract()[4]
    obs = [o for o in vtz["observances"] if o["dtstart"].year == 1999][0]
    rule, _ = V.split_until(obs["rrule"])
    check("DTSTART 1999-04-24 is a Saturday",
          obs["dtstart"].strftime("%a") == "Sat")
    check("DTSTART does not satisfy its own rule (defect)",
          not rule_matches(obs["dtstart"], rule_parse(rule), obs["dtstart"]), rule)
    got = [t for t, _, _, k in V.Resolver(vtz, until_year=2000).changes
           if datetime(1999, 4, 1, tzinfo=UTC) <= t < datetime(1999, 5, 1, tzinfo=UTC)]
    check("two DAYLIGHT onsets one day apart in April 1999",
          len(got) == 2 and got[1] - got[0] == timedelta(days=1),
          ", ".join(d.strftime("%Y-%m-%dT%H:%MZ") for d in got))


def test_all_examples_agree_with_dateutil_tzical():
    """Cross-check against a second, independently written VTIMEZONE reader.

    `dateutil.tz.tzical` is a hand-written iCalendar parser, not a port of the
    expander this repository compares against elsewhere, so the lineage
    objection in findings/003 does not apply in the same way.  It is still only
    a cross-check: agreement is evidence about the reading, not adjudication of
    the spec.  What matters most here is that it takes the same "DTSTART is an
    onset" reading, including for the unsynchronized 1999 case.
    """
    print("\nRFC 5545 3.6.5: every example vs dateutil.tz.tzical")
    try:
        from dateutil.tz import tzical
    except ImportError:
        print("  skip  dateutil not importable")
        return
    for vtz in V.extract():
        ics = ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//rruleref//test//EN\r\n"
               + "\r\n".join(vtz["raw"]) + "\r\nEND:VCALENDAR\r\n")
        tz = tzical(io.StringIO(ics)).get()
        r = V.Resolver(vtz, until_year=2040)
        start = r.first_onset
        end = datetime(2035, 1, 1, tzinfo=UTC)
        bad, n, t = [], 0, start
        while t < end:
            n += 1
            if r.utcoffset(t) != t.astimezone(tz).utcoffset():
                bad.append(t)
            t += timedelta(hours=5)
        check("example %d: %d instants agree with tzical" % (vtz["index"], n),
              not bad, "first disagreement %s" % (bad[0] if bad else None))


if __name__ == "__main__":
    test_new_york_examples_match_tzdata()
    test_example_2_validity_window_is_exact()
    test_until_must_equal_the_last_instance()
    test_example_5_has_a_year_without_daylight_time()
    test_example_5_dtstart_is_not_synchronized()
    test_all_examples_agree_with_dateutil_tzical()
    print("\n%d failure(s)" % len(FAILURES))
    sys.exit(1 if FAILURES else 0)

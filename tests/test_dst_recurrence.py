"""Known-answer tests for recurrence instances that land on an ambiguous or
nonexistent local time.

Section 3.8.5.3's 39 worked examples (checked in `test_tz.py`) all place their
occurrences at unambiguous local times, so they say nothing about what happens
when the *computed* start time of an instance falls in a daylight-saving gap or
repeat.  The RFC answers that question directly, in the RECUR value type,
section 3.3.10:

    "If the computed local start time of a recurrence instance does not
     exist, or occurs more than once, for the specified time zone, the
     time of the recurrence instance is interpreted in the same manner
     as an explicit DATE-TIME value describing that date and time, as
     specified in Section 3.3.5."

So the applicability question is settled by the spec and does not have to be
argued: a generated instance is localized by exactly the same two rules as a
literal DATE-TIME.  Section 3.3.5:

    "If, based on the definition of the referenced time zone, the local time
     described occurs more than once (when changing from daylight to standard
     time), the DATE-TIME value refers to the first occurrence of the
     referenced time."

    "If the local time described does not occur (when changing from standard
     to daylight time), the DATE-TIME value is interpreted using the UTC
     offset before the gap in local times."

What the RFC does *not* supply here is printed expected values.  So each
expected column below is derived, and the derivation is stated per case:

  * ambiguous instance  -> the offset in effect immediately *before* the
    transition instant ("the first occurrence");
  * nonexistent instance -> the offset in effect immediately *before* the gap;
  * every other instance -> the zone's unique offset for that local time.

The transition instants themselves are not asserted from memory.  They are read
back out of the system tz database by `_transitions()` and printed by the test,
so a reader can check that the case really straddles the transition it claims
to, and a tzdata change that moved a transition would show up as a changed
banner rather than as a silent pass.

Four zones are covered deliberately: America/New_York (one-hour, northern),
Australia/Sydney (one-hour, southern, so the spring/autumn months are swapped),
Australia/Lord_Howe (a **30-minute** shift, which catches code that assumes a
gap is an hour wide), and Europe/Dublin (whose transitions are at 01:00 local,
not 02:00).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, "/home/agent/terrarium/scratch/pylibs")
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import tzexpand

FAILURES = []
M = 60  # minutes per hour, for readable offset literals


def check(name, cond, extra=""):
    print("%s %s  %s" % ("PASS" if cond else "FAIL", name, extra))
    if not cond:
        FAILURES.append(name)


def _transitions(tzid, year):
    """Return the UTC-offset changes of `tzid` during `year`, from tzdata.

    Scanned at 15-minute resolution -- finer than any transition granularity in
    the database, so no transition can be stepped over -- and then bisected to
    the second, so the reported instant is the transition itself and not merely
    the sample that followed it.
    """
    tz = ZoneInfo(tzid)
    out, prev = [], None
    t = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    while t < end:
        off = t.astimezone(tz).utcoffset()
        if prev is not None and off != prev[1]:
            lo, hi = prev[0], t          # lo has the old offset, hi the new one
            while (hi - lo) > timedelta(seconds=1):
                mid = lo + (hi - lo) / 2
                if mid.astimezone(tz).utcoffset() == prev[1]:
                    lo = mid
                else:
                    hi = mid
            out.append((lo.astimezone(tz), prev[1], hi.astimezone(tz), off))
        prev = (t, off)
        t += timedelta(minutes=15)
    return out


# Each case: (id, tzid, dtstart, rrule, why, [(local, offset_minutes), ...])
CASES = [
    # -------------------------------------------------- America/New_York, 2026
    # autumn: 2026-11-01 02:00 EDT -> 01:00 EST, so 01:00..01:59 occurs twice.
    ("ny-daily-ambiguous", "America/New_York", "20261031T013000",
     "FREQ=DAILY;COUNT=3",
     "11-01 01:30 occurs twice; 3.3.5 takes the first, i.e. EDT (-04:00)",
     [("20261031T013000", -4 * M), ("20261101T013000", -4 * M),
      ("20261102T013000", -5 * M)]),
    # spring: 2026-03-08 02:00 EST -> 03:00 EDT, so 02:00..02:59 does not exist.
    ("ny-daily-nonexistent", "America/New_York", "20260307T023000",
     "FREQ=DAILY;COUNT=3",
     "03-08 02:30 does not exist; 3.3.5 uses the offset before the gap, EST "
     "(-05:00), so it denotes the instant printed as 03:30 EDT",
     [("20260307T023000", -5 * M), ("20260308T023000", -5 * M),
      ("20260309T023000", -4 * M)]),
    ("ny-weekly-ambiguous", "America/New_York", "20261025T013000",
     "FREQ=WEEKLY;COUNT=3", "same repeat, reached weekly rather than daily",
     [("20261025T013000", -4 * M), ("20261101T013000", -4 * M),
      ("20261108T013000", -5 * M)]),
    ("ny-monthly-ambiguous", "America/New_York", "20261001T013000",
     "FREQ=MONTHLY;BYMONTHDAY=1;COUNT=3",
     "same repeat, reached by BYMONTHDAY expansion",
     [("20261001T013000", -4 * M), ("20261101T013000", -4 * M),
      ("20261201T013000", -5 * M)]),
    ("ny-byhour-nonexistent", "America/New_York", "20260306T020000",
     "FREQ=DAILY;BYHOUR=2;BYMINUTE=0;COUNT=4",
     "the gap hour reached by BYHOUR expansion rather than inherited from "
     "DTSTART, which is a different code path in most implementations",
     [("20260306T020000", -5 * M), ("20260307T020000", -5 * M),
      ("20260308T020000", -5 * M), ("20260309T020000", -4 * M)]),
    ("ny-hourly-ambiguous", "America/New_York", "20261101T000000",
     "FREQ=HOURLY;COUNT=5",
     "hourly in *local* time across the repeat: 01:00 is ambiguous and takes "
     "EDT, so the 01:00 EST hour is never produced at all",
     [("20261101T000000", -4 * M), ("20261101T010000", -4 * M),
      ("20261101T020000", -5 * M), ("20261101T030000", -5 * M),
      ("20261101T040000", -5 * M)]),
    ("ny-hourly-nonexistent", "America/New_York", "20260308T000000",
     "FREQ=HOURLY;COUNT=5",
     "hourly in *local* time across the gap: 02:00 does not exist and is "
     "interpreted at the pre-gap offset, which is the same instant as 03:00",
     [("20260308T000000", -5 * M), ("20260308T010000", -5 * M),
      ("20260308T020000", -5 * M), ("20260308T030000", -4 * M),
      ("20260308T040000", -4 * M)]),
    ("ny-minutely-nonexistent", "America/New_York", "20260308T015800",
     "FREQ=MINUTELY;COUNT=4",
     "minute resolution walking into the gap",
     [("20260308T015800", -5 * M), ("20260308T015900", -5 * M),
      ("20260308T020000", -5 * M), ("20260308T020100", -5 * M)]),

    # --------------------------------------------- Australia/Sydney, southern
    # autumn: 2026-04-05 03:00 AEDT -> 02:00 AEST (April, not November).
    ("syd-daily-ambiguous", "Australia/Sydney", "20260404T023000",
     "FREQ=DAILY;COUNT=3",
     "southern hemisphere: the repeat is in April; first occurrence is AEDT "
     "(+11:00)",
     [("20260404T023000", 11 * M), ("20260405T023000", 11 * M),
      ("20260406T023000", 10 * M)]),
    # spring: 2026-10-04 02:00 AEST -> 03:00 AEDT.
    ("syd-daily-nonexistent", "Australia/Sydney", "20261003T023000",
     "FREQ=DAILY;COUNT=3",
     "southern hemisphere: the gap is in October; pre-gap offset is AEST "
     "(+10:00)",
     [("20261003T023000", 10 * M), ("20261004T023000", 10 * M),
      ("20261005T023000", 11 * M)]),

    # ------------------------------------- Australia/Lord_Howe, 30-minute DST
    # autumn: 2026-04-05 02:00 (+11) -> 01:30 (+10:30); 01:30..01:59 repeats.
    ("lhi-daily-ambiguous", "Australia/Lord_Howe", "20260404T014500",
     "FREQ=DAILY;COUNT=3",
     "a 30-minute repeat, not an hour: only 01:30..01:59 is ambiguous, so "
     "01:45 is inside it and 01:15 would not be",
     [("20260404T014500", 11 * M), ("20260405T014500", 11 * M),
      ("20260406T014500", 10 * M + 30)]),
    # spring: 2026-10-04 02:00 (+10:30) -> 02:30 (+11); 02:00..02:29 is a gap.
    ("lhi-daily-nonexistent", "Australia/Lord_Howe", "20261003T021500",
     "FREQ=DAILY;COUNT=3",
     "a 30-minute gap: 02:15 does not exist but 02:45 does",
     [("20261003T021500", 10 * M + 30), ("20261004T021500", 10 * M + 30),
      ("20261005T021500", 11 * M)]),
    ("lhi-daily-outside-gap", "Australia/Lord_Howe", "20261003T024500",
     "FREQ=DAILY;COUNT=3",
     "control for the case above: 02:45 is past the 30-minute gap and exists "
     "on every one of these days, so no 3.3.5 rule applies to it",
     [("20261003T024500", 10 * M + 30), ("20261004T024500", 11 * M),
      ("20261005T024500", 11 * M)]),

    # ------------------------------------------- Europe/Dublin, 01:00 changes
    ("dub-daily-nonexistent", "Europe/Dublin", "20260328T013000",
     "FREQ=DAILY;COUNT=3",
     "Dublin changes at 01:00 local, not 02:00: 03-29 01:30 does not exist "
     "and takes the pre-gap offset, GMT (+00:00)",
     [("20260328T013000", 0), ("20260329T013000", 0),
      ("20260330T013000", 1 * M)]),
    ("dub-daily-ambiguous", "Europe/Dublin", "20261024T013000",
     "FREQ=DAILY;COUNT=3",
     "10-25 01:30 occurs twice; the first occurrence is IST (+01:00)",
     [("20261024T013000", 1 * M), ("20261025T013000", 1 * M),
      ("20261026T013000", 0)]),
]


def _got(expander, case):
    _id, tzid, dtstart, rule, _why, want = case
    dt = datetime.strptime(dtstart, "%Y%m%dT%H%M%S")
    dts = expander(rule, dt, tzid, limit=max(len(want) + 2, 8))
    return [(d.strftime("%Y%m%dT%H%M%S"),
             int(d.utcoffset().total_seconds() // 60)) for d in dts]


def _dateutil_expand(rule, dtstart_naive, tzid, limit=8):
    from dateutil.rrule import rrulestr
    aware = dtstart_naive.replace(tzinfo=ZoneInfo(tzid))
    it = rrulestr(rule, dtstart=aware)
    out = []
    for d in it:
        out.append(d)
        if len(out) >= limit:
            break
    return out


def run_table(label, expander):
    print("\n--- %s ---" % label)
    for case in CASES:
        cid, tzid, _dtstart, rule, why, want = case
        try:
            got = _got(expander, case)
        except Exception as e:
            check("%s: %s" % (label, cid), False, "%s: %s" % (type(e).__name__, e))
            continue
        ok = got[:len(want)] == want
        extra = why if ok else ("want %s got %s" % (want, got[:len(want)]))
        check("%s: %s" % (label, cid), ok, extra)


def test_transition_banner():
    print("Transitions read from the installed tz database (local time one second\nbefore the change, then at the change), for the cases below:")
    for tzid, year in [("America/New_York", 2026), ("Australia/Sydney", 2026),
                       ("Australia/Lord_Howe", 2026), ("Europe/Dublin", 2026)]:
        for a, aoff, b, boff in _transitions(tzid, year):
            print("  %-20s %s %s -> %s %s"
                  % (tzid, a.strftime("%Y-%m-%d %H:%M:%S"), a.tzname(),
                     b.strftime("%Y-%m-%d %H:%M:%S"), b.tzname()))


def test_instant_level_consequences():
    """Two consequences of 3.3.10 + 3.3.5 that are easy to disbelieve.

    Neither is a defect in anything; both follow from the rule that expansion
    happens in local time and each computed local time is then localized.
    """
    ny = "America/New_York"

    # Autumn, FREQ=HOURLY: 06:00Z (= 01:00 EST) is never generated, because the
    # only local time that would map to it, 01:00, was already resolved to its
    # *first* occurrence at 05:00Z.  An "hourly" rule therefore has a two-hour
    # real-time gap once a year.
    got = [d.astimezone(timezone.utc).strftime("%H:%M")
           for d in tzexpand.expand("FREQ=HOURLY;COUNT=5",
                                    datetime(2026, 11, 1, 0, 0), ny, limit=5)]
    check("autumn FREQ=HOURLY skips one hour of real time (no 06:00Z)",
          got == ["04:00", "05:00", "07:00", "08:00", "09:00"], str(got))

    # Spring, FREQ=HOURLY: 02:00 (nonexistent, pre-gap offset) and 03:00 denote
    # the *same* instant, so the recurrence set contains two instances one hour
    # apart in local time and zero seconds apart in real time.
    inst = [d.astimezone(timezone.utc)
            for d in tzexpand.expand("FREQ=HOURLY;COUNT=5",
                                     datetime(2026, 3, 8, 0, 0), ny, limit=5)]
    check("spring FREQ=HOURLY puts two instances at the same instant",
          inst[2] == inst[3] and inst[2].strftime("%H:%M") == "07:00",
          "%s vs %s" % (inst[2].isoformat(), inst[3].isoformat()))
    # ...and the sequence is still non-decreasing, so a consumer that assumes
    # *strictly* increasing instants is the thing that breaks, not the spec.
    check("instants are non-decreasing but not strictly increasing",
          all(inst[i] <= inst[i + 1] for i in range(len(inst) - 1))
          and not all(inst[i] < inst[i + 1] for i in range(len(inst) - 1)),
          str([d.strftime("%H:%M") for d in inst]))


def test_dtstart_fold_is_not_honoured():
    """A DTSTART pinned to the *second* occurrence is not expressible.

    Python can represent the second occurrence of an ambiguous local time with
    `fold=1`, but RFC 5545 cannot: 3.3.5 says the value "refers to the first
    occurrence".  A conforming expander must therefore ignore an incoming
    fold=1 rather than propagate it.
    """
    d = tzexpand.expand("FREQ=DAILY;COUNT=1",
                        datetime(2026, 11, 1, 1, 30, fold=1),
                        "America/New_York", limit=1)[0]
    check("fold=1 on DTSTART is discarded (3.3.5 takes the first occurrence)",
          d.utcoffset() == timedelta(hours=-4), d.strftime("%Z%z"))


if __name__ == "__main__":
    test_transition_banner()
    run_table("rruleref", tzexpand.expand)
    run_table("dateutil", _dateutil_expand)
    print()
    test_instant_level_consequences()
    test_dtstart_fold_is_not_honoured()
    print("\n%d failure(s)" % len(FAILURES))
    sys.exit(1 if FAILURES else 0)

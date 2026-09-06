"""Timezone-aware expansion: wall-clock recurrence, then RFC 5545 localization.

RFC 5545 computes a recurrence in the *local* time of `DTSTART` and attaches
the referenced time zone to each result; the UTC offset of an occurrence is
therefore whatever that zone says on that date, and it changes across a
daylight-saving transition without the wall-clock time changing. That is why
the worked examples in section 3.8.5.3 print `9:00 AM EDT` before the November
transition and `9:00 AM EST` after it, for the same rule.

Two rules from the spec are implemented here, both quoted in full because
getting them backwards is the classic defect:

section 3.3.5, on a local time that occurs twice (autumn transition):

    "If, based on the definition of the referenced time zone, the local time
     described occurs more than once (when changing from daylight to standard
     time), the DATE-TIME value refers to the first occurrence of the
     referenced time."

section 3.3.5, on a local time that does not occur (spring transition):

    "If the local time described does not occur (when changing from standard
     to daylight time), the DATE-TIME value is interpreted using the UTC
     offset before the gap in local times."

Both are exactly Python's `fold=0` semantics under `zoneinfo`, which is the
reason `localize` below is one line and this docstring is long: the claim being
made is that the one line is *the spec's rule*, and it is checked against the
spec's own two printed examples in `tests/test_tz.py`.

section 3.3.10, on `UNTIL` when `DTSTART` carries a time zone:

    "If the 'DTSTART' property is specified as a date with UTC time or a date
     with local time and time zone reference, then the UNTIL rule part MUST be
     specified as a date with UTC time."

so `UNTIL` bounds the recurrence as an *instant*, not as a wall-clock time.
Comparing it against local time is an offset-sized error that only shows up
near a transition, which is why it is easy to ship.
"""

import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from naive import expand as naive_expand


def localize(naive_dt, tzid):
    """Attach `tzid` to a wall-clock datetime under RFC 5545 section 3.3.5.

    `fold=0` is both Python's default and the spec's rule: for an ambiguous
    local time it selects the first (daylight) occurrence, and for a
    nonexistent one it uses the offset in effect before the gap.
    """
    return naive_dt.replace(tzinfo=ZoneInfo(tzid), fold=0)


def _split_until(rrule):
    """Remove UNTIL from a rule, returning (rule_without_until, until_utc|None)."""
    kept, until = [], None
    for part in rrule.split(";"):
        if part.upper().startswith("UNTIL="):
            v = part.split("=", 1)[1]
            if v.endswith("Z"):
                until = datetime.strptime(v[:-1], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
            elif "T" in v:
                until = datetime.strptime(v, "%Y%m%dT%H%M%S")  # local time; DTSTART is floating
            else:
                until = datetime.strptime(v, "%Y%m%d")
        else:
            kept.append(part)
    return ";".join(kept), until


def expand(rrule, dtstart_naive, tzid, limit=64, horizon_years=40):
    """Expand `rrule` from a wall-clock DTSTART in `tzid`, returning aware datetimes.

    UNTIL is stripped before the wall-clock expansion and re-applied afterwards
    as an instant comparison, which is what section 3.3.10 requires when
    DTSTART carries a time zone. COUNT is applied after UNTIL.
    """
    rule, until = _split_until(rrule)
    m = re.search(r"(?:^|;)COUNT=(\d+)", rule, re.I)
    count = int(m.group(1)) if m else None
    if count is not None:
        rule = re.sub(r"(?:^|;)COUNT=\d+", "", rule, flags=re.I).lstrip(";")

    want = limit if count is None else max(limit, count)
    horizon = dtstart_naive + timedelta(days=365 * horizon_years + horizon_years // 4)
    wall = naive_expand(rule, dtstart_naive, horizon=horizon, limit=want)

    if tzid is None:
        out = wall
        if until is not None:
            out = [d for d in out if d <= until]
    else:
        out = [localize(d, tzid) for d in wall]
        if until is not None:
            if until.tzinfo is None:
                raise ValueError("DTSTART has a TZID, so UNTIL must be a UTC value "
                                 "(RFC 5545 section 3.3.10)")
            out = [d for d in out if d.astimezone(timezone.utc) <= until]
    if count is not None:
        out = out[:count]
    return out[:limit] if count is None else out

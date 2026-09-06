"""A deliberately naive RFC 5545 RRULE expander.

Written from the spec text (RFC 5545 sec. 3.3.10), not ported from any
existing implementation, so that disagreements with a real library are
evidence about one of us rather than a shared ancestry bug.

Strategy: brute-force. Enumerate every candidate datetime in a window and ask
"is this an occurrence?" as a pure predicate. That is far slower than the
interval-skipping machinery real libraries use, and far easier to check by eye
against the spec. BYSETPOS is the one part that cannot be a per-instant
predicate, so it is applied afterwards by grouping matches into periods.
"""

from datetime import datetime, date, timedelta
from calendar import monthrange, isleap

FREQS = ("SECONDLY", "MINUTELY", "HOURLY", "DAILY", "WEEKLY", "MONTHLY", "YEARLY")
DAYS = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")


def parse(rrule):
    """Parse an RRULE property value into a dict. Accepts a leading 'RRULE:'."""
    if rrule.upper().startswith("RRULE:"):
        rrule = rrule[6:]
    out = {}
    for part in rrule.split(";"):
        if not part:
            continue
        k, _, v = part.partition("=")
        k = k.upper()
        if k in ("FREQ", "WKST"):
            out[k] = v.upper()
        elif k in ("INTERVAL", "COUNT"):
            out[k] = int(v)
        elif k == "UNTIL":
            out[k] = _parse_until(v)
        elif k == "BYDAY":
            out[k] = [_parse_byday(x) for x in v.split(",")]
        else:
            out[k] = [int(x) for x in v.split(",")]
    out.setdefault("FREQ", None)
    out.setdefault("INTERVAL", 1)
    out.setdefault("WKST", "MO")
    return out


def _parse_until(v):
    v = v.rstrip("Z")
    if "T" in v:
        return datetime.strptime(v, "%Y%m%dT%H%M%S")
    return datetime.strptime(v, "%Y%m%d")


def _parse_byday(tok):
    tok = tok.upper()
    day = tok[-2:]
    ordinal = tok[:-2]
    return (int(ordinal) if ordinal not in ("", "+", "-") else None, day)


# --- period arithmetic -----------------------------------------------------
# Each FREQ turns a datetime into an integer period index. INTERVAL then keeps
# only the periods whose index is congruent to DTSTART's.

def _week_index(d, wkst):
    """Weeks since epoch, where a week begins on wkst."""
    shift = DAYS.index(wkst)
    return (d.toordinal() - 1 - shift) // 7


def period_index(dt, freq, wkst):
    if freq == "YEARLY":
        return dt.year
    if freq == "MONTHLY":
        return dt.year * 12 + (dt.month - 1)
    if freq == "WEEKLY":
        return _week_index(dt.date(), wkst)
    if freq == "DAILY":
        return dt.toordinal()
    if freq == "HOURLY":
        return dt.toordinal() * 24 + dt.hour
    if freq == "MINUTELY":
        return (dt.toordinal() * 24 + dt.hour) * 60 + dt.minute
    if freq == "SECONDLY":
        return ((dt.toordinal() * 24 + dt.hour) * 60 + dt.minute) * 60 + dt.second
    raise ValueError(freq)


# --- BY-rule predicates ----------------------------------------------------

def _monthday_matches(dt, vals):
    last = monthrange(dt.year, dt.month)[1]
    for v in vals:
        if v > 0 and dt.day == v:
            return True
        if v < 0 and dt.day == last + 1 + v:
            return True
    return False


def _yearday_matches(dt, vals):
    n = 366 if isleap(dt.year) else 365
    doy = dt.timetuple().tm_yday
    for v in vals:
        if v > 0 and doy == v:
            return True
        if v < 0 and doy == n + 1 + v:
            return True
    return False


def _weekno_matches(dt, vals, wkst):
    """RFC 5545: week numbering follows ISO 8601 generalised to any WKST --
    week 1 is the first week with at least 4 days in the year."""
    got = _week_number(dt.date(), wkst)
    if got is None:
        return False
    year, num = got
    total = _weeks_in_year(year, wkst)
    for v in vals:
        if v > 0 and num == v:
            return True
        if v < 0 and num == total + 1 + v:
            return True
    return False


def _week_start(d, wkst):
    shift = (d.weekday() - DAYS.index(wkst)) % 7
    return d - timedelta(days=shift)


def _weeks_in_year(year, wkst):
    """Number of numbered weeks in `year` under this WKST."""
    jan1 = date(year, 1, 1)
    first = _week_start(jan1, wkst)
    if (first + timedelta(days=6) - jan1).days >= 3:
        week1 = first          # >=4 days of this week fall in the year
    else:
        week1 = first + timedelta(days=7)
    nxt = _first_week_start(year + 1, wkst)
    return (nxt - week1).days // 7


def _first_week_start(year, wkst):
    jan1 = date(year, 1, 1)
    first = _week_start(jan1, wkst)
    if (first + timedelta(days=6) - jan1).days >= 3:
        return first
    return first + timedelta(days=7)


def _week_number(d, wkst):
    """(owning year, week number) or None if d falls before week 1 of its own
    year -- in which case it belongs to the last week of the previous year."""
    for y in (d.year + 1, d.year, d.year - 1):
        start = _first_week_start(y, wkst)
        if start <= d < _first_week_start(y + 1, wkst):
            return y, (d - start).days // 7 + 1
    return None


def _byday_matches(dt, vals, freq, has_bymonth):
    """BYDAY entries may carry an ordinal (e.g. -1FR). Per the spec the ordinal
    is only meaningful when FREQ is MONTHLY, or YEARLY; and under YEARLY with
    BYMONTH present the ordinal counts within the month, not the year."""
    wd = DAYS[dt.weekday()]
    for ordinal, day in vals:
        if day != wd:
            continue
        if ordinal is None:
            return True
        if freq == "MONTHLY" or (freq == "YEARLY" and has_bymonth):
            n, total = _nth_in_span(dt, dt.replace(day=1).date(),
                                    date(dt.year, dt.month,
                                         monthrange(dt.year, dt.month)[1]))
        elif freq == "YEARLY":
            n, total = _nth_in_span(dt, date(dt.year, 1, 1), date(dt.year, 12, 31))
        else:
            # Ordinal is not allowed here; the spec calls it an error. Treat it
            # as unmatchable rather than silently ignoring the ordinal.
            continue
        if ordinal > 0 and n == ordinal:
            return True
        if ordinal < 0 and n == total + 1 + ordinal:
            return True
    return False


def _nth_in_span(dt, lo, hi):
    """Which occurrence of dt's weekday is dt within [lo, hi], and how many are
    there in total."""
    d = dt.date()
    first = lo + timedelta(days=(d.weekday() - lo.weekday()) % 7)
    n = (d - first).days // 7 + 1
    total = (hi - first).days // 7 + 1
    return n, total


# --- the occurrence predicate ---------------------------------------------

def _finer(freq):
    """Datetime components strictly finer than freq, coarse to fine."""
    order = ["YEARLY", "MONTHLY", "DAILY", "HOURLY", "MINUTELY", "SECONDLY"]
    comp = {"YEARLY": "month", "MONTHLY": "day", "DAILY": "hour",
            "HOURLY": "minute", "MINUTELY": "second"}
    if freq == "WEEKLY":
        return ["hour", "minute", "second"]
    i = order.index(freq)
    return [comp[order[j]] for j in range(i, len(order) - 1)]


def matches(dt, r, dtstart):
    """Is `dt` an occurrence of rule `r`, ignoring BYSETPOS/COUNT/UNTIL?"""
    freq, wkst = r["FREQ"], r["WKST"]

    if (period_index(dt, freq, wkst) - period_index(dtstart, freq, wkst)) \
            % r["INTERVAL"] != 0:
        return False

    if "BYMONTH" in r and dt.month not in r["BYMONTH"]:
        return False
    if "BYWEEKNO" in r and not _weekno_matches(dt, r["BYWEEKNO"], wkst):
        return False
    if "BYYEARDAY" in r and not _yearday_matches(dt, r["BYYEARDAY"]):
        return False
    if "BYMONTHDAY" in r and not _monthday_matches(dt, r["BYMONTHDAY"]):
        return False
    if "BYDAY" in r and not _byday_matches(dt, r["BYDAY"], freq, "BYMONTH" in r):
        return False
    if "BYHOUR" in r and dt.hour not in r["BYHOUR"]:
        return False
    if "BYMINUTE" in r and dt.minute not in r["BYMINUTE"]:
        return False
    if "BYSECOND" in r and dt.second not in r["BYSECOND"]:
        return False

    if freq == "WEEKLY" and "BYDAY" not in r and dt.weekday() != dtstart.weekday():
        return False

    # Components finer than FREQ that no BY rule pins down inherit DTSTART's
    # value. This is what stops FREQ=MONTHLY from firing on all 31 days.
    for comp in _finer(freq):
        if comp in _pinned(r, freq):
            continue
        if getattr(dt, comp) != getattr(dtstart, comp):
            return False
    return True


def _pinned(r, freq):
    """Which finer-than-FREQ components are determined by a BY rule."""
    out = set()
    if "BYMONTH" in r:
        out.add("month")
    day_rules = [k for k in ("BYMONTHDAY", "BYYEARDAY", "BYDAY", "BYWEEKNO") if k in r]
    if day_rules:
        out.add("day")
        # Under YEARLY the day-level rules all *expand* over the whole year
        # (RFC 5545 table in 3.3.10), so they pick the month too. Under
        # MONTHLY they only pick a day within the period's month.
        if freq == "YEARLY":
            out.add("month")
    if "BYHOUR" in r:
        out.add("hour")
    if "BYMINUTE" in r:
        out.add("minute")
    if "BYSECOND" in r:
        out.add("second")
    return out


def expand(rrule, dtstart, horizon=None, limit=1000):
    """Return occurrences at or after dtstart, in order."""
    r = parse(rrule)
    freq = r["FREQ"]
    if horizon is None:
        horizon = dtstart + timedelta(days=365 * 30 + 8)
    if "UNTIL" in r and r["UNTIL"] < horizon:
        horizon = r["UNTIL"]

    out = []
    setpos = "BYSETPOS" in r
    cap = min(limit, r["COUNT"]) if "COUNT" in r else limit

    def flush(got):
        """Apply BYSETPOS to one completed period's matches."""
        got.sort()
        picked = set()
        for p in r["BYSETPOS"]:
            if p > 0 and p <= len(got):
                picked.add(got[p - 1])
            elif p < 0 and -p <= len(got):
                picked.add(got[p])
        out.extend(x for x in sorted(picked) if x >= dtstart)

    # BYSETPOS needs a whole period before it can select from it, so matches
    # are buffered per period. The buffer is flushed as soon as the candidate
    # stream leaves that period -- candidates arrive in increasing time order,
    # so a period that has been left is complete. Accumulating every period to
    # the horizon first was correct but unusable below FREQ=DAILY:
    # FREQ=SECONDLY;BYSETPOS=-1 enumerated ~10^9 candidates before returning
    # its first occurrence.
    cur_key, cur = None, []
    for dt in _candidates(r, dtstart, horizon, whole_period=setpos):
        if dt > horizon or (not setpos and dt < dtstart):
            continue
        if setpos:
            key = period_index(dt, freq, r["WKST"])
            if key != cur_key:
                if cur_key is not None:
                    flush(cur)
                    if len(out) >= cap:
                        return out[:cap]
                cur_key, cur = key, []
            if matches(dt, r, dtstart):
                cur.append(dt)
        elif matches(dt, r, dtstart):
            out.append(dt)
            if len(out) >= cap:
                return out[:cap]

    if setpos and cur_key is not None:
        flush(cur)
    return out[:cap]


def _period_start(dt, freq, wkst):
    if freq == "YEARLY":
        return dt.replace(month=1, day=1)
    if freq == "MONTHLY":
        return dt.replace(day=1)
    if freq == "WEEKLY":
        d = _week_start(dt.date(), wkst)
        return dt.replace(year=d.year, month=d.month, day=d.day)
    return dt


def _candidates(r, dtstart, horizon, whole_period=False):
    """Every datetime worth testing. Times finer than the rule can vary are
    fixed to DTSTART's, which keeps the brute force affordable."""
    freq = r["FREQ"]
    hours = sorted(r["BYHOUR"]) if "BYHOUR" in r else (
        list(range(24)) if freq in ("HOURLY", "MINUTELY", "SECONDLY") else [dtstart.hour])
    mins = sorted(r["BYMINUTE"]) if "BYMINUTE" in r else (
        list(range(60)) if freq in ("MINUTELY", "SECONDLY") else [dtstart.minute])
    secs = sorted(r["BYSECOND"]) if "BYSECOND" in r else (
        list(range(60)) if freq == "SECONDLY" else [dtstart.second])

    begin = _period_start(dtstart, freq, r["WKST"]) if whole_period else dtstart
    d = begin.date()
    end = horizon.date()
    while d <= end:
        for h in hours:
            for mi in mins:
                for s in secs:
                    yield datetime(d.year, d.month, d.day, h, mi, s)
        d += timedelta(days=1)

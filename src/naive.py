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


def period_index(dt, freq, wkst, week_based_year=False):
    if freq == "YEARLY":
        if week_based_year:
            # The rival reading of 3.3.10 recorded as `week_based_year`: a
            # BYWEEKNO occurrence belongs to the period of the year that *owns*
            # its week, not to the calendar year the day happens to sit in.
            # See finding 059. Only reached when the caller asked for it and
            # the rule actually carries BYWEEKNO.
            got = _week_number(dt.date(), wkst)
            return got[0] if got else dt.year
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
    wy = r.get("_WEEK_BASED_YEAR", False)

    if (period_index(dt, freq, wkst, wy) - period_index(dtstart, freq, wkst, wy)) \
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


#: The default expansion horizon, in days from DTSTART. THIS IS THE ONLY
#: DEFINITION of the number. `differ.py` used to carry a second copy, and
#: finding 064 found that the two were obeyed inconsistently: callers that
#: went through `compare()` saw one horizon and callers that relied on this
#: default saw the other, with nothing to make them disagree loudly. A
#: horizon defined in two modules is a horizon only one of them can be
#: changed by. See standing rule 66.
HORIZON_DAYS = 365 * 300


def expand(rrule, dtstart, horizon=None, limit=1000,
           truncate_first_period=False, week_based_year=False):
    """Return occurrences at or after dtstart, in order.

    ``truncate_first_period`` selects the *other* reading of the question in
    finding 004: when true, the period containing DTSTART is cut at DTSTART
    before BYSETPOS selects from it, so BYSETPOS=1 can name DTSTART itself.
    The default (false) is this expander's normal reading -- BYSETPOS selects
    from the whole period and instances before DTSTART are then dropped.

    Nothing in the corpus is built with this flag set. It exists so that
    ``src/reading_dependence.py`` can ask which corpus cases would change
    answer under the other reading, which is a different question from which
    cases two implementations happen to disagree about. See finding 018.
    """
    r = parse(rrule)
    freq = r["FREQ"]
    # `week_based_year` only means anything for a YEARLY rule carrying
    # BYWEEKNO; everywhere else the two readings are the same expander, so the
    # flag is normalised away here and no other code has to re-check it.
    r["_WEEK_BASED_YEAR"] = bool(week_based_year) and freq == "YEARLY" \
        and "BYWEEKNO" in r
    if horizon is None:
        horizon = dtstart + timedelta(days=HORIZON_DAYS)
    out = []
    setpos = "BYSETPOS" in r
    until = r.get("UNTIL")
    # RFC 5545 3.3.10 fixes the order: "... BYSECOND and BYSETPOS; then COUNT
    # and UNTIL are evaluated." Folding UNTIL into the candidate horizon
    # evaluates it *before* BYSETPOS, which truncates the final period and can
    # therefore change which instance BYSETPOS selects. Without BYSETPOS the
    # two orders coincide and clipping is a large speedup; with it, candidates
    # run to the end of the period containing UNTIL and UNTIL is applied after
    # the selection. Found by property P3 (src/properties.py), 2026-09-07;
    # this is the last-period twin of finding 004's first-period truncation.
    if until is not None and not setpos and until < horizon:
        horizon = until
    # The caller's horizon is subject to exactly the same ordering argument as
    # UNTIL: cutting the candidate stream at it truncates the period BYSETPOS
    # is selecting from, so the last occurrence returned could be one no
    # complete expansion would ever contain. Under BYSETPOS the period
    # containing the horizon is therefore completed and the horizon applied
    # afterwards. `stop` is the cut the caller asked for; `scan` is how far
    # candidates must run to answer it.
    stop = horizon
    scan = horizon + _period_span(freq) if setpos else horizon
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
        out.extend(x for x in sorted(picked)
                   if x >= dtstart and x <= stop
                   and (until is None or x <= until))

    # BYSETPOS needs a whole period before it can select from it, so matches
    # are buffered per period. The buffer is flushed as soon as the candidate
    # stream leaves that period -- candidates arrive in increasing time order,
    # so a period that has been left is complete. Accumulating every period to
    # the horizon first was correct but unusable below FREQ=DAILY:
    # FREQ=SECONDLY;BYSETPOS=-1 enumerated ~10^9 candidates before returning
    # its first occurrence.
    cur_key, cur = None, []
    for dt in _candidates(r, dtstart, scan, whole_period=setpos):
        if dt > scan or ((not setpos or truncate_first_period) and dt < dtstart):
            continue
        if setpos:
            key = period_index(dt, freq, r["WKST"],
                               r.get("_WEEK_BASED_YEAR", False))
            if key != cur_key:
                if cur_key is not None:
                    flush(cur)
                    if len(out) >= cap:
                        return out[:cap]
                # Candidates arrive in increasing time order, so a period
                # whose first candidate is past UNTIL cannot contribute.
                if dt > stop or (until is not None and dt > until):
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


#: An upper bound on the length of one FREQ period, used only to finish the
#: period a horizon falls inside. Deliberately generous; it bounds scanning,
#: it does not define any answer.
_SPAN = {"YEARLY": timedelta(days=400), "MONTHLY": timedelta(days=40),
         "WEEKLY": timedelta(days=10), "DAILY": timedelta(days=2),
         "HOURLY": timedelta(hours=2), "MINUTELY": timedelta(minutes=2),
         "SECONDLY": timedelta(seconds=2)}


def _period_span(freq):
    return _SPAN[freq]


def _period_start(dt, freq, wkst, week_based_year=False):
    if freq == "YEARLY":
        if week_based_year:
            got = _week_number(dt.date(), wkst)
            d = _first_week_start(got[0] if got else dt.year, wkst)
            return dt.replace(year=d.year, month=d.month, day=d.day)
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

    begin = _period_start(dtstart, freq, r["WKST"],
                          r.get("_WEEK_BASED_YEAR", False)) \
        if whole_period else dtstart
    d = begin.date()
    end = horizon.date()
    while d <= end:
        for h in hours:
            for mi in mins:
                for s in secs:
                    yield datetime(d.year, d.month, d.day, h, mi, s)
        d += timedelta(days=1)

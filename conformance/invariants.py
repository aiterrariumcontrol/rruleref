"""Corpus-independent conformance checks.

`score.py` compares an adapter against `expect`, so every failure it reports is
a *disagreement with this corpus* and inherits whatever is wrong with it. This
module asks a question that never consults `expect`:

    does each occurrence an implementation returned satisfy the rule's own
    BY parts?

That question is only neutral for *some* parts, and getting this wrong is easy.
RFC 5545 sec. 3.3.10 fixes an application order (line 2418 of the RFC text):

    BYMONTH, BYWEEKNO, BYYEARDAY, BYMONTHDAY, BYDAY, BYHOUR, BYMINUTE,
    BYSECOND and BYSETPOS

and a table classifying each part, per FREQ, as Expand, Limit or N/A. A Limit
only removes candidates, so a constraint it imposes survives to the output. An
Expand *adds* candidates, and an Expand applied after part P can add dates that
do not satisfy P. So:

    P's constraint is guaranteed to hold in the output iff no part applied
    after P expands the same component (date, or hour/minute/second).

Everything else is exactly the contested territory -- `FREQ=WEEKLY;BYMONTH=7`
with `BYDAY` expanding the week across a month boundary is finding 004's
dispute, not a defect -- and this module reports it separately and scores
nothing on it. An earlier version of this file checked every part
unconditionally and would have published 31 non-conformance claims against
ical4j that are all order-dependent readings.

Also deliberately not checked: missing occurrences, ordering, UNTIL/COUNT
bounds, and the ordinal of a numeric BYDAY (`1FR` -- only the weekday is
checked; the ordinal's period is what the table decides).
"""
import re, datetime, calendar

WD = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]

#: RFC 5545 sec. 3.3.10 application order, line 2418. BYSETPOS is a Limit for
#: every FREQ and is applied last, so it never breaks a surviving constraint.
ORDER = ["BYMONTH", "BYWEEKNO", "BYYEARDAY", "BYMONTHDAY", "BYDAY",
         "BYHOUR", "BYMINUTE", "BYSECOND"]

#: The component each part constrains. An Expand can only invalidate an earlier
#: part that constrains the *same* component: BYHOUR never moves a date.
COMPONENT = {"BYMONTH": "date", "BYWEEKNO": "date", "BYYEARDAY": "date",
             "BYMONTHDAY": "date", "BYDAY": "date",
             "BYHOUR": "hour", "BYMINUTE": "minute", "BYSECOND": "second"}

FREQS = ["SECONDLY", "MINUTELY", "HOURLY", "DAILY", "WEEKLY", "MONTHLY", "YEARLY"]

#: The table at RFC 5545 lines 2431-2452, transcribed. E=Expand, L=Limit, -=N/A.
TABLE = {
    "BYMONTH":    "LLLLLLE",
    "BYWEEKNO":   "------E",
    "BYYEARDAY":  "LLL---E",
    "BYMONTHDAY": "LLLL-EE",
    "BYDAY":      "LLLLE12",   # 1, 2 = Note 1, Note 2
    "BYHOUR":     "LLLEEEE",
    "BYMINUTE":   "LLEEEEE",
    "BYSECOND":   "LEEEEEE",
}


def parts(rrule):
    out = {}
    for p in rrule.split(";"):
        k, _, v = p.partition("=")
        out[k.upper()] = v
    return out


def classify(part, freq, present):
    """'Expand', 'Limit' or None (N/A), per the table and its two notes."""
    row = TABLE.get(part)
    if row is None or freq not in FREQS:
        return None
    c = row[FREQS.index(freq)]
    if c == "1":                                    # Note 1, MONTHLY
        return "Limit" if "BYMONTHDAY" in present else "Expand"
    if c == "2":                                    # Note 2, YEARLY
        return ("Limit" if ("BYYEARDAY" in present or "BYMONTHDAY" in present)
                else "Expand")
    return {"E": "Expand", "L": "Limit", "-": None}[c]


def survives(part, freq, present):
    """True when part's constraint must hold in the output; see module docstring."""
    if classify(part, freq, present) is None:
        return False
    comp = COMPONENT[part]
    for later in ORDER[ORDER.index(part) + 1:]:
        if later in present and COMPONENT[later] == comp \
                and classify(later, freq, present) == "Expand":
            return False
    return True


def _ints(v):
    return [int(x) for x in v.split(",") if x]


def _check(part, d, p):
    """The violation detail for `part` at datetime `d`, or None."""
    v = p[part]
    if part == "BYMONTH" and d.month not in _ints(v):
        return "month %d not in %s" % (d.month, v)
    if part == "BYMONTHDAY":
        last = calendar.monthrange(d.year, d.month)[1]
        ok = sorted(set(n if n > 0 else last + 1 + n for n in _ints(v)))
        if d.day not in ok:
            return "day %d not in %s (month has %d days)" % (d.day, ok, last)
    if part == "BYDAY":
        names = set(re.sub(r"^[+-]?\d+", "", x).upper() for x in v.split(",") if x)
        if WD[d.weekday()] not in names:
            return "weekday %s not in %s" % (WD[d.weekday()], v)
    if part == "BYYEARDAY":
        ylen = 366 if calendar.isleap(d.year) else 365
        ok = sorted(set(n if n > 0 else ylen + 1 + n for n in _ints(v)))
        yd = d.timetuple().tm_yday
        if yd not in ok:
            return "yearday %d not in %s" % (yd, ok)
    for pt, val in (("BYHOUR", d.hour), ("BYMINUTE", d.minute), ("BYSECOND", d.second)):
        if part == pt and val not in _ints(v):
            return "%d not in %s" % (val, v)
    return None


def violations(rrule, occurrences):
    """Yield (occurrence, part, detail, guaranteed).

    `guaranteed` is True when no part applied later expands the same component,
    so the constraint must hold under any reading of the table. When it is
    False the mismatch is an order-dependent reading, reported but not scored.
    """
    p = parts(rrule)
    freq = p.get("FREQ", "")
    for o in occurrences:
        try:
            d = datetime.datetime.strptime(o, "%Y%m%dT%H%M%S")
        except ValueError:
            yield (o, "FORMAT", "not YYYYMMDDTHHMMSS", True)
            continue
        for part in ORDER:
            if part not in p or classify(part, freq, p) is None:
                continue
            detail = _check(part, d, p)
            if detail:
                yield (o, part, detail, survives(part, freq, p))

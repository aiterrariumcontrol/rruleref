"""Predict ical4j 4.3.0's FREQ=YEARLY output from its BY-rule pipeline alone.

Reimplements only what Recur.getCandidates does for FREQ=YEARLY when the rule
parts are drawn from {FREQ, INTERVAL, WKST, BYMONTH, BYYEARDAY, BYMONTHDAY,
BYDAY, BYSETPOS}, plus the RecurDateSpliterator loop that drives it:

  seed_k = DTSTART + k*INTERVAL years, k = 0, 1, 2, ...
  dates = [seed_k]
  BYMONTH     -> expand: replace MONTH_OF_YEAR on each date (day clamped)
  BYYEARDAY   -> expand: replace DAY_OF_YEAR within *the date's year*
  BYMONTHDAY  -> expand: replace DAY_OF_MONTH within *the date's month*
                 (or, when BYYEARDAY/BYDAY/BYWEEKNO and BYMONTHDAY are all
                 absent, an implicit BYMONTHDAY = DTSTART's day of month)
  BYDAY       -> limit when BYYEARDAY or BYMONTHDAY is present (and then an
                 ordinal BYDAY matches nothing: finding 051's defect B); else
                 expand over the month when BYMONTH is present; else the year
  BYSETPOS    -> sort, then index; nothing deduplicates first
  sort; keep candidates >= DTSTART and <= DTSTART+10958d until `limit`

The two expansion scopes in the middle are the point: BYMONTHDAY expands
within the enclosing *month* of the incoming date, BYYEARDAY within the
enclosing *year*. See finding 056.
"""
import calendar
import json
import sys
from datetime import datetime, timedelta

WD = {'MO': 0, 'TU': 1, 'WE': 2, 'TH': 3, 'FR': 4, 'SA': 5, 'SU': 6}
SCOPE = {'FREQ', 'INTERVAL', 'WKST', 'BYMONTH', 'BYYEARDAY', 'BYMONTHDAY',
         'BYDAY', 'BYSETPOS'}
MAX_INCREMENT_COUNT = 1000          # Recur.KEY_MAX_INCREMENT_COUNT default
HORIZON_DAYS = 10958                # the adapter's periodEnd


def parse(rrule):
    return dict(p.split('=', 1) for p in rrule.split(';'))


def in_scope(rrule):
    p = parse(rrule)
    return p.get('FREQ') == 'YEARLY' and not (set(p) - SCOPE)


def _mlen(y, m):
    return calendar.monthrange(y, m)[1]


def _ylen(y):
    return 366 if calendar.isleap(y) else 365


def with_month(d, m):
    """LocalDateTime.with(MONTH_OF_YEAR, m): day clamped (resolvePreviousValid)."""
    return d.replace(month=m, day=min(d.day, _mlen(d.year, m)))


def _from_doy(d, n):
    m = 1
    while n > _mlen(d.year, m):
        n -= _mlen(d.year, m)
        m += 1
    return d.replace(month=m, day=n)


def by_month(dates, months):
    return [with_month(d, m) for d in dates for m in months]


def by_year_day(dates, yeardays):
    out = []
    for d in dates:
        n = _ylen(d.year)
        for yd in yeardays:
            if yd == 0 or yd < -n or yd > n:
                continue
            out.append(_from_doy(d, yd if yd > 0 else n + 1 + yd))
    return out


def by_month_day(dates, monthdays):
    out = []
    for d in dates:
        length = _mlen(d.year, d.month)
        maxlen = 31 if d.month in (1, 3, 5, 7, 8, 10, 12) else (30 if d.month != 2 else 29)
        for md in monthdays:
            if maxlen < abs(md):
                continue
            if md > 0:
                if length < md:
                    continue            # Skip.OMIT
                out.append(d.replace(day=md))
            else:
                if -length > md:
                    continue            # Skip.OMIT
                out.append(d.replace(day=length + 1 + md))
    return out


def _offset(dates, off):
    if off == 0:
        return list(dates)
    n = len(dates)
    if off < 0 and off >= -n:
        return [dates[n + off]]
    if off > 0 and off <= n:
        return [dates[off - 1]]
    return []


def by_day(dates, daylist, mode):
    """daylist: list of (offset, weekday). mode: 'limit' | 'month' | 'year'."""
    out = []
    for d in dates:
        if mode == 'limit':
            # ByDayRule.LimitFilter compares whole WeekDay values, ordinal
            # included, against a plain WeekDay -- so an ordinal BYDAY never
            # matches here. Finding 051's defect B, reproduced rather than
            # re-derived.
            transformed = [d] if (0, d.weekday()) in daylist else []
        elif mode == 'month':
            transformed = [d.replace(day=i) for i in range(1, _mlen(d.year, d.month) + 1)]
            transformed = [c for c in transformed if c.weekday() in {w for _, w in daylist}]
        else:
            transformed = [_from_doy(d, i) for i in range(1, _ylen(d.year) + 1)]
            transformed = [c for c in transformed if c.weekday() in {w for _, w in daylist}]
        for off, w in daylist:
            out.extend(_offset([c for c in transformed if c.weekday() == w], off))
    return out


def by_set_pos(dates, setpos):
    dates = sorted(dates)
    n = len(dates)
    out = []
    for s in setpos:
        if 0 < s <= n:
            out.append(dates[s - 1])
        elif -n <= s < 0:
            out.append(dates[n + s])
    return out


def parse_byday(spec):
    out = []
    for tok in spec.split(','):
        tok = tok.strip()
        wd = WD[tok[-2:]]
        off = int(tok[:-2]) if len(tok) > 2 else 0
        out.append((off, wd))
    return out


def candidates(p, root_seed, seed_k):
    months = [int(x) for x in p['BYMONTH'].split(',')] if 'BYMONTH' in p else []
    yeardays = [int(x) for x in p['BYYEARDAY'].split(',')] if 'BYYEARDAY' in p else []
    monthdays = [int(x) for x in p['BYMONTHDAY'].split(',')] if 'BYMONTHDAY' in p else []
    daylist = parse_byday(p['BYDAY']) if 'BYDAY' in p else []
    setpos = [int(x) for x in p['BYSETPOS'].split(',')] if 'BYSETPOS' in p else []

    dates = [seed_k]
    if months:
        dates = by_month(dates, months)
    if yeardays:
        dates = by_year_day(dates, yeardays)
    if monthdays:
        dates = by_month_day(dates, monthdays)
    elif not yeardays and not daylist:
        # Recur.getCandidates' implicit BYMONTHDAY for YEARLY
        dates = by_month_day(dates, [root_seed.day])
    if daylist:
        # deriveFilterType(): DAILY (limit) when BYYEARDAY or BYMONTHDAY present,
        # else MONTHLY when BYMONTH present, else YEARLY.
        if yeardays or monthdays:
            mode = 'limit'
        elif months:
            mode = 'month'
        else:
            mode = 'year'
        dates = by_day(dates, daylist, mode)
    if setpos:
        dates = by_set_pos(dates, setpos)
    return sorted(dates)


def predict(rrule, dtstart, limit):
    p = parse(rrule)
    if not in_scope(rrule):
        raise ValueError('out of scope: ' + rrule)
    interval = int(p.get('INTERVAL', 1))
    seed = datetime.strptime(dtstart, '%Y%m%dT%H%M%S')
    end = seed + timedelta(days=HORIZON_DAYS)
    out = []
    empty_runs = 0
    k = 0
    last = None
    while len(out) < limit:
        if last is not None and last > end:
            break
        seed_k = seed.replace(year=seed.year + interval * k) if _safe(seed, interval * k) \
            else _shift_years(seed, interval * k)
        cands = candidates(p, seed, seed_k)
        if not cands:
            empty_runs += 1
            if empty_runs > MAX_INCREMENT_COUNT or seed_k > end:
                break
        else:
            empty_runs = 0
        for c in cands:
            last = c
            if c >= seed and c <= end:
                out.append(c)
                if len(out) >= limit:
                    break
        k += 1
    return [d.strftime('%Y%m%dT%H%M%S') for d in sorted(out)][:limit]


def _safe(seed, years):
    try:
        seed.replace(year=seed.year + years)
        return True
    except ValueError:
        return False


def _shift_years(seed, years):
    # Feb 29 + n years where the target year is not a leap year: java.time
    # LocalDateTime.plusYears clamps to Feb 28.
    y = seed.year + years
    return seed.replace(year=y, day=min(seed.day, _mlen(y, seed.month)))


if __name__ == '__main__':
    for line in sys.stdin:
        if not line.strip():
            continue
        c = json.loads(line)
        print(json.dumps({'id': c['id'],
                          'occurrences': predict(c['rrule'], c['dtstart'], c['limit'])}))

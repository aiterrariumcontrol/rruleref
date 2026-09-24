"""Replay DateTime::Event::ICal::recur()'s ARGUMENT ASSEMBLY, in Python.

This module is the CLAIM.  It says: given an RRULE, DT::E::ICal does not
evaluate the rule -- it rewrites the rule into a fixed set-algebra expression
over DateTime::Event::Recurrence primitives, and returns whatever that
expression happens to mean.  The expression is emitted as JSON and evaluated by
findings/repro/079-eval-expr.pl, which loads DateTime::Event::Recurrence and
never loads DateTime::Event::ICal.

So the prediction is falsifiable in the way standing rule 81 requires: if the
expression this file builds is not the expression recur() builds, the evaluated
output will differ from the adapter's recorded output, element for element.

Transcribed from /usr/share/perl5/DateTime/Event/ICal.pm 0.13, subs
_secondly_recurrence .. _yearly_recurrence, _recur_1fr, and recur().  Structure
and ORDER are preserved deliberately, including the destructive deletes from
the argument hash -- the deletes are the mechanism, not an implementation
detail.
"""
import json, re, sys, copy

WEEKDAYS = {'mo': 1, 'tu': 2, 'we': 3, 'th': 4, 'fr': 5, 'sa': 6, 'su': 7}


def rec(base, **by):
    return {"op": "recurrence", "base": base, "args": by}


def _int_list(v):
    return list(v) if isinstance(v, list) else [v]


# ---------------------------------------------------------------- handlers
# Each takes (dtstart, args) where args is the live dict recur() is mutating,
# and returns an expression.  dtstart is a dict with year/month/day/hour/
# minute/second/dow (1=Mon..7=Sun).

def _time_fills(dtstart, args, by, upto):
    """The identical five lines at the head of every handler: a BY part that is
    absent is replaced by DTSTART's value for that field, so the handler always
    produces a fully-specified time-of-day."""
    if 'bysecond' in upto:
        by['seconds'] = args.get('bysecond', dtstart['second'])
    if 'byminute' in upto:
        by['minutes'] = args.get('byminute', dtstart['minute'])
    if 'byhour' in upto:
        by['hours'] = args.get('byhour', dtstart['hour'])


def _secondly(dtstart, args):
    by = {"start": True}
    if 'interval' in args: by['interval'] = args['interval']
    args.pop('interval', None)
    return rec('secondly', **by)


def _minutely(dtstart, args):
    by = {"start": True}
    if 'interval' in args: by['interval'] = args['interval']
    _time_fills(dtstart, args, by, ('bysecond',))
    for k in ('interval', 'bysecond'): args.pop(k, None)
    return rec('minutely', **by)


def _hourly(dtstart, args):
    by = {"start": True}
    if 'interval' in args: by['interval'] = args['interval']
    _time_fills(dtstart, args, by, ('bysecond', 'byminute'))
    for k in ('interval', 'byminute', 'bysecond'): args.pop(k, None)
    return rec('hourly', **by)


def _daily(dtstart, args):
    by = {"start": True}
    if 'interval' in args: by['interval'] = args['interval']
    _time_fills(dtstart, args, by, ('bysecond', 'byminute', 'byhour'))
    had_bymonth = 'bymonth' in args
    had_bymonthday = 'bymonthday' in args
    for k in ('interval', 'bysecond', 'byminute', 'byhour'): args.pop(k, None)
    # the handler writes BACK into the caller's hash
    if had_bymonth and not had_bymonthday:
        args['bymonthday'] = list(range(1, 32))
    return rec('daily', **by)


def _weekly(dtstart, args, notes=None):
    by = {"start": True}
    if 'interval' in args: by['interval'] = args['interval']
    _time_fills(dtstart, args, by, ('bysecond', 'byminute', 'byhour'))
    by['week_start_day'] = args['wkst'] if args.get('wkst') else 'mo'
    if 'byday' in args:
        # s/[-+\d]+// -- the ordinal is STRIPPED, not honoured.
        raw = _int_list(args['byday'])
        if notes is not None and any(strip_ordinal(d) != d for d in raw):
            notes.add('weekly-handler-strips-byday-ordinal')
        by['days'] = [WEEKDAYS[strip_ordinal(d)] for d in raw]
    else:
        if notes is not None:
            notes.add('weekly-handler-fills-byday-from-dtstart-weekday')
        by['days'] = dtstart['dow']
    for k in ('interval', 'bysecond', 'byminute', 'byhour', 'byday'):
        args.pop(k, None)
    return rec('weekly', **by)


ORDINAL_RUN = re.compile(r'[-+\d]+')


def strip_ordinal(d):
    r"""s/[\-\+\d]+// -- one non-global substitution: the first run of sign or
    digit characters is removed and the rest of the token is the day name."""
    return ORDINAL_RUN.sub('', d, count=1)


def _monthly(dtstart, args, notes=None):
    by = {"start": True}
    if 'interval' in args: by['interval'] = args['interval']
    _time_fills(dtstart, args, by, ('bysecond', 'byminute', 'byhour'))
    by['week_start_day'] = args['wkst'] if args.get('wkst') else '1mo'
    if 'bymonthday' in args:
        by['days'] = args['bymonthday']
    elif 'byday' in args:
        by['days'] = list(range(1, 32))
    else:
        if notes is not None:
            notes.add('base:day-pinned-to-dtstart-day')
        by['days'] = dtstart['day']
    set_byday = None
    if 'byday' in args:
        sub = {}
        _time_fills(dtstart, args, sub, ('bysecond', 'byminute', 'byhour'))
        set_byday = _recur_1fr(sub, args['byday'], 'monthly')
        args.pop('byday', None)
    for k in ('interval', 'bysecond', 'byminute', 'byhour', 'bymonthday'):
        args.pop(k, None)
    base = rec('monthly', **by)
    if set_byday:
        return {"op": "intersection", "terms": [base, set_byday]}
    return base


def _yearly(dtstart, args, notes=None, tag=''):
    """NOTE the snapshot.  Every handler in ICal.pm opens with

        my %args = %$argsref;

    and thereafter READS the snapshot while DELETING from the caller's live
    hash.  So a key this sub has already consumed is still visible to its own
    later tests -- which is why `FREQ=YEARLY;BYMONTH=4;BYDAY=-1TH` reaches the
    `_recur_1fr` call with freq='monthly' even though `bymonth` was deleted
    twenty lines earlier, and why the BYWEEKNO branch builds a BYDAY set as
    well as having already consumed BYDAY.  Both are load-bearing."""
    snap = dict(args)
    by = {"start": True}
    if 'interval' in snap: by['interval'] = snap['interval']
    _time_fills(dtstart, snap, by, ('bysecond', 'byminute', 'byhour'))
    by['week_start_day'] = snap['wkst'] if snap.get('wkst') else 'mo'

    def note(b):
        if notes is not None:
            notes.add(tag + b)

    if 'bymonth' in snap:
        note('yearly-branch-bymonth')
        by['months'] = snap['bymonth']
        args.pop('bymonth', None)
        if 'bymonthday' in snap:
            by['days'] = snap['bymonthday']
        elif 'byday' in snap:
            by['days'] = list(range(1, 32))
        else:
            note('day-pinned-to-dtstart-day')
            by['days'] = dtstart['day']
        args.pop('bymonthday', None)
    elif 'byweekno' in snap:
        note('yearly-branch-byweekno')
        by['weeks'] = snap['byweekno']
        args.pop('byweekno', None)
        by['days'] = snap['byday'] if 'byday' in snap else dtstart['dow']
        args.pop('byday', None)
    elif 'byyearday' in snap:
        note('yearly-branch-byyearday')
        by['days'] = snap['byyearday']
        args.pop('byyearday', None)
    elif 'byday' in snap:
        note('yearly-branch-byday')
        by['months'] = list(range(1, 13))
        by['days'] = snap['bymonthday'] if 'bymonthday' in snap else list(range(1, 32))
        args.pop('bymonthday', None)
    else:
        note('yearly-branch-fallback-month-pinned-to-dtstart-month')
        by['months'] = dtstart['month']
        if 'bymonthday' not in snap:
            note('day-pinned-to-dtstart-day')
        by['days'] = snap['bymonthday'] if 'bymonthday' in snap else dtstart['day']
        args.pop('bymonthday', None)

    set_byday = None
    if 'byday' in snap:
        note('byday-reapplied-via-recur-1fr')
        # the snapshot still has bymonth here even when the branch above
        # deleted it -- this is what makes the sub-set MONTHLY, not yearly
        freq = 'monthly' if 'bymonth' in snap else 'yearly'
        sub = {}
        _time_fills(dtstart, snap, sub, ('bysecond', 'byminute', 'byhour'))
        set_byday = _recur_1fr(sub, snap['byday'], freq)
        args.pop('byday', None)
    for k in ('interval', 'byday', 'bysecond', 'byminute', 'byhour'):
        args.pop(k, None)
    base = rec('yearly', **by)
    if set_byday:
        return {"op": "intersection", "terms": [base, set_byday]}
    return base


def _recur_1fr(timeargs, byday, freq):
    """'1FR' and 'FR' in one BYDAY become two DIFFERENT kinds of set, unioned:
    unindexed weekdays become a weekly recurrence; each indexed weekday becomes
    a monthly-or-yearly recurrence whose week_start_day is that weekday."""
    days, no_index = {}, []
    for d in _int_list(byday):
        # /(.*)(\w\w)/ -- greedy, so the last two word chars are the day name
        count, name = d[:-2], d[-2:]
        wd = WEEKDAYS.get(name)
        if not wd:
            return {"op": "die", "msg": "invalid week day (%s)" % name}
        if count:
            days.setdefault(name, []).append(int(count))
        else:
            no_index.append(wd)
    result = None
    if no_index:
        a = dict(timeargs); a['days'] = no_index
        result = rec('weekly', **a)
    for name in days:
        a = dict(timeargs)
        a['weeks'] = days[name]
        a['week_start_day'] = '1' + name
        term = rec('monthly' if freq == 'monthly' else 'yearly', **a)
        result = {"op": "union", "terms": [result, term]} if result else term
    return result


def _call(h, dtstart, args, notes, tag):
    if h is _yearly:
        return _yearly(dtstart, args, notes, tag)
    if h is _weekly:
        return _weekly(dtstart, args, notes)
    if h is _monthly:
        return _monthly(dtstart, args, notes)
    return h(dtstart, args)


FREQ_HANDLER = {'secondly': _secondly, 'minutely': _minutely, 'hourly': _hourly,
                'daily': _daily, 'weekly': _weekly, 'monthly': _monthly,
                'yearly': _yearly}


# ------------------------------------------------------------------ recur()

def decompose(rrule, dtstart):
    """Returns (expression, notes).  `notes` names each mechanism the assembly
    actually exercised for THIS rule, so membership is recorded, not inferred."""
    args = parse(rrule)
    backup = copy.deepcopy(args)
    notes = set()

    count = args.pop('count', None)
    until = args.pop('until', None)

    interval = args.get('interval') or 1
    args['interval'] = interval

    if args['freq'] == 'daily' and 'bymonth' in args and interval == 1:
        args['freq'] = 'yearly'
        if 'bymonthday' not in args:
            args['bymonthday'] = list(range(1, 32))
        notes.add('daily-bymonth-rewritten-to-yearly')

    h = FREQ_HANDLER.get(args['freq'])
    if h is None:
        return {"op": "die", "msg": "invalid freq"}, ['invalid-freq']
    base_set = _call(h, dtstart, args, notes, 'base:')

    if 'wkst' in args:
        notes.add('wkst-discarded')
    args.pop('wkst', None)

    by_year_day = None
    if 'byyearday' in args:
        by_year_day = _yearly(dtstart, args, notes, 'aux-byyearday:')

    by_month_day = None
    if 'bymonthday' in args or 'bymonth' in args:
        by = dict(args)
        _aux_time_fill(by, backup, args['freq'])
        by_month_day = _yearly(dtstart, by, notes, 'aux-bymonth(day):')
        args.pop('bymonthday', None)
        args.pop('bymonth', None)

    by_week_day = None
    if 'byday' in args or 'byweekno' in args:
        by = dict(args)
        _aux_time_fill(by, backup, args['freq'])
        if 'byweekno' in by:
            notes.add('byweekno-discarded-unread')
        by_week_day = _weekly(dtstart, by, notes)
        args.pop('byday', None)
        args.pop('byweekno', None)

    by_hour = None
    if 'byhour' in args:
        by = dict(args)
        _aux_time_fill(by, backup, args['freq'], hours=False)
        by_hour = _daily(dtstart, by)
        args.pop('byhour', None)

    expr = base_set
    for aux in (by_year_day, by_month_day, by_week_day, by_hour):
        if aux is None:
            continue
        expr = {"op": "intersection", "terms": [expr, aux]} if expr else aux

    if 'bysetpos' in args:
        expr = {"op": "bysetpos", "freq": args['freq'],
                "pos": _int_list(args['bysetpos']), "recurrence": expr}
        args.pop('bysetpos', None)
        notes.add('bysetpos')

    args.pop('freq', None)
    leftover = sorted(args)
    if leftover:
        notes.add('die-unimplemented:' + ','.join(leftover))
        return ({"op": "die",
                 "msg": "these arguments are not implemented: " + ','.join(leftover)},
                sorted(notes))

    return {"op": "span", "dtstart": True, "until": until, "count": count,
            "expr": expr}, sorted(notes)


def _aux_time_fill(by, backup, freq, hours=True):
    """recur() restores the time-of-day BY parts from its untouched backup copy
    before each auxiliary handler, and widens the one matching the frequency to
    its full range."""
    if hours:
        if backup.get('byhour'): by['byhour'] = backup['byhour']
        if freq == 'hourly': by['byhour'] = list(range(0, 24))
    if backup.get('byminute'): by['byminute'] = backup['byminute']
    if freq == 'minutely': by['byminute'] = list(range(0, 60))
    if backup.get('bysecond'): by['bysecond'] = backup['bysecond']
    if freq == 'secondly': by['bysecond'] = list(range(0, 60))


INTLIST = {'bysecond', 'byminute', 'byhour', 'bymonthday', 'byyearday',
           'byweekno', 'bymonth', 'bysetpos'}


def parse(rrule):
    args = {}
    for part in rrule.split(';'):
        k, _, v = part.partition('=')
        if not v:
            continue
        k = k.lower()
        if k == 'freq':
            args['freq'] = v.lower()
        elif k in ('interval', 'count'):
            args[k] = int(v)
        elif k == 'until':
            args['until'] = v.rstrip('Z')
        elif k == 'wkst':
            args['wkst'] = v.lower()
        elif k == 'byday':
            args['byday'] = [x.lower() for x in v.split(',')]
        elif k in INTLIST:
            args[k] = [int(x) for x in v.split(',')]
        else:
            raise ValueError('unsupported rule part: ' + k)
    return args


def dtparts(s):
    y, mo, d = int(s[0:4]), int(s[4:6]), int(s[6:8])
    import datetime as _dt
    dow = _dt.date(y, mo, d).isoweekday()
    return {"year": y, "month": mo, "day": d, "hour": int(s[9:11]),
            "minute": int(s[11:13]), "second": int(s[13:15]), "dow": dow,
            "s": s}


if __name__ == '__main__':
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        c = json.loads(line)
        ds = dtparts(c['dtstart'])
        try:
            expr, notes = decompose(c['rrule'], ds)
        except Exception as e:
            expr, notes = {"op": "die", "msg": str(e)}, ['predictor-error']
        print(json.dumps({"id": c["id"], "dtstart": c["dtstart"],
                          "limit": c["limit"], "expr": expr, "notes": notes}))

"""Attribute sabre/vobject's residual mismatches by REPRODUCING each one exactly.

    TZ=UTC python3 conformance/score.py --json out.json -- \
        php conformance/adapters/php/vobject_adapter.php
    python3 findings/repro/076-attribute-sabre-residual.py out.json [--verify]

sabre/vobject fails 980 of this corpus's 1727 cases, the largest block on the
board and the only one never decomposed with recorded membership.  Finding 031
characterised one mechanism on one cluster (BYMONTH absent from the WEEKLY and
MONTHLY code paths, 244 of 244) and measured the same rewrite across the rest of
the corpus, where it fell apart: 6/73 at DAILY, 0/41 at YEARLY.  So the rewrite
that 031 found is not the model; it is one instance of a wider one.

The wider model is read off `lib/Recur/RRuleIterator.php`, not guessed from
output (standing rule 81).  That file has one `next*()` method per FREQ, and
each method reads a FIXED SUBSET of the parsed BY fields.  A BY part outside its
FREQ's subset is not mishandled -- it is never read.  So the prediction is:

    sabre's output == the rule with its unsupported BY parts DELETED,
                      expanded correctly.

Per FREQ, what the code actually reads:

  HOURLY    nothing at all.  nextHourly() adds INTERVAL hours and returns.
  DAILY     BYHOUR, BYDAY, BYMONTH            (nextDaily()'s do/while)
  WEEKLY    BYHOUR, BYDAY, WKST               (nextWeekly()'s do/while)
  MONTHLY   BYMONTHDAY, BYDAY, BYSETPOS       (via getMonthlyOccurrences())
  YEARLY    BYMONTH; then BYMONTHDAY, BYDAY, BYSETPOS inside the month.
            With no BYMONTH: BYWEEKNO, else BYYEARDAY, else plain yearly --
            and those two branches are mutually exclusive and consume BYDAY as
            a weekday filter.
  MINUTELY  no case in next()'s switch; the date never advances.
  SECONDLY  likewise.

The oracle is python-dateutil, used ONLY as a rule evaluator (standing rule 24);
it is not evidence about the right answer.  The mutation is the claim, dateutil
merely computes it.

--verify is the load-bearing part (standing rule 82).  Deleting BY parts makes
rules STRICTLY LOOSER, so a deletion model predicts long lists that are cheap to
be wrong about in a different direction from 075's empty ones: a mechanism that
deletes a part sabre really does read would still reproduce every case where the
part happens not to matter.  The replay runs every mechanism over all the cases
sabre PASSES and requires none of them to claim a different answer there.
"""
import json, sys, os, collections
from datetime import datetime, date, timedelta

sys.path.insert(0, "src")
try:
    import env; env.add_dateutil_to_path()
except Exception:
    pass
from dateutil.rrule import rrulestr

FMT = "%Y%m%dT%H%M%S"

# What each next*() method reads.  Everything else in the rule is unread.
READS = {
    'HOURLY':   set(),
    'DAILY':    {'BYHOUR', 'BYDAY', 'BYMONTH'},
    'WEEKLY':   {'BYHOUR', 'BYDAY', 'WKST'},
    'MONTHLY':  {'BYMONTHDAY', 'BYDAY', 'BYSETPOS'},
}
ALL_BY = ['BYSECOND', 'BYMINUTE', 'BYHOUR', 'BYDAY', 'BYMONTHDAY',
          'BYYEARDAY', 'BYWEEKNO', 'BYMONTH', 'BYSETPOS']


def parts(r):
    out = {}
    for p in r.split(';'):
        k, _, v = p.partition('='); out[k] = v
    return out


def ev(rrule, dtstart, limit):
    try:
        rr = rrulestr("RRULE:" + rrule, dtstart=datetime.strptime(dtstart, FMT))
        out = []
        for x in rr:
            if len(out) >= limit: break
            out.append(x.strftime(FMT))
        return out
    except Exception:
        return None


def keep_only(r, keep):
    """Delete every BY part (and WKST) the code path does not read."""
    out = []
    for p in r.split(';'):
        k = p.split('=')[0]
        if k in ALL_BY or k == 'WKST':
            if k not in keep:
                continue
        out.append(p)
    return ';'.join(out)


def yearly_keep(p):
    """nextYearly()'s branches are mutually exclusive, in this order."""
    if p.get('BYMONTH'):
        return {'BYMONTH', 'BYMONTHDAY', 'BYDAY', 'BYSETPOS'}
    if p.get('BYWEEKNO'):
        return {'BYWEEKNO', 'BYDAY'}
    if p.get('BYYEARDAY'):
        return {'BYYEARDAY', 'BYDAY'}
    return set()


# ------------------------------------------------------------- mechanism 1
def unread_parts(c):
    """The rule with everything its FREQ's method never reads deleted."""
    p = parts(c['rrule'])
    f = p.get('FREQ')
    keep = yearly_keep(p) if f == 'YEARLY' else READS.get(f)
    if keep is None:
        return None
    stripped = keep_only(c['rrule'], keep)
    if stripped == c['rrule']:
        return None                  # vacuous: nothing to delete, no claim
    return ev(stripped, c['dtstart'], c['limit'])

# ------------------------------------------------------------- mechanism 2
def daily_fast_path(c):
    """nextDaily() returns EARLY when the rule has neither BYHOUR nor BYDAY.

        if (!$this->byHour && !$this->byDay) {
            $this->advanceTheDate('+'.$this->interval.' days');
            return;
        }

    The BYMONTH filter sits in the do/while below that return, so a DAILY rule
    carrying BYMONTH and nothing else reads NOTHING -- 031's rewrite kept
    BYMONTH at DAILY and that is why it scored 6 of 73 there."""
    p = parts(c['rrule'])
    if p.get('FREQ') != 'DAILY' or p.get('BYHOUR') or p.get('BYDAY'):
        return None
    stripped = keep_only(c['rrule'], set())
    if stripped == c['rrule']:
        return None
    return ev(stripped, c['dtstart'], c['limit'])


# ------------------------------------------------------------- mechanism 3
def never_advances(c):
    """next()'s switch has no case for 'minutely' or 'secondly'.

    Neither branch is taken, currentDate is never modified, and the counter
    still increments -- so the iterator yields DTSTART again, and again, for as
    long as anything asks.  This is not the documented infinite loop (that one
    hangs); it terminates, and returns an unbounded run of one instant."""
    p = parts(c['rrule'])
    if p.get('FREQ') not in ('MINUTELY', 'SECONDLY'):
        return None
    n = c['limit']
    if p.get('COUNT'):
        n = min(n, int(p['COUNT']))
    return [c['dtstart']] * n


# ------------------------------------------------------------- mechanism 4/5
def php_add_years(d, n):
    """PHP's modify('+N years') keeps the day number and overflows the month:
    2028-02-29 +1 year is 2029-03-01, not 2029-02-28."""
    y = d.year + n
    try:
        return d.replace(year=y)
    except ValueError:                      # 29 Feb into a common year
        return date(y, 3, d.day - 28)


def iso_setdate(y, w, dow):
    """PHP DateTime::setISODate(y, w, dow), which is plain arithmetic and
    accepts out-of-range w and dow rather than rejecting them."""
    jan4 = date(y, 1, 4)
    week1_monday = jan4 - timedelta(days=jan4.isoweekday() - 1)
    return week1_monday + timedelta(days=(w - 1) * 7 + (dow - 1))


DAYMAP = {'SU': 0, 'MO': 1, 'TU': 2, 'WE': 3, 'TH': 4, 'FR': 5, 'SA': 6}


def yearly_no_bymonth(c):
    """Simulate nextYearly()'s no-BYMONTH branch step for step.

    Two defects live in it and they interact:

    (a) THE LEAP-DAY GUARD IS ABSORBING.  Before BYWEEKNO and BYYEARDAY are
        ever consulted, the method checks whether the CURRENT occurrence falls
        on 29 February and, if it does, walks forward by INTERVAL years until
        it lands in February again -- and returns.  So the first occurrence
        that happens to be a leap day hijacks the whole remaining series and
        pins it to 29 February for ever.  FREQ=YEARLY;BYYEARDAY=+60 from
        2026-03-01 is correct for three occurrences, reaches 2028-02-29, and
        then emits 2032, 2036, 2040 ... and never day 60 again.

    (b) THE WEEKDAY INDEX IS OFF BY ONE.  Both branches build their day offsets
        from $dayMap, which numbers SU=0 .. SA=6, and then compare them against
        format('N') (BYYEARDAY) or hand them to setISODate() (BYWEEKNO), both
        of which number MO=1 .. SU=7.  MO..SA survive by coincidence; BYDAY=SU
        matches nothing at all at BYYEARDAY, and selects the SUNDAY OF THE
        PREVIOUS WEEK at BYWEEKNO.  With no BYDAY the BYWEEKNO branch defaults
        to the bare offset 1 -- one day per week, Monday -- where RFC 5545
        expands the whole week.
    """
    p = parts(c['rrule'])
    if p.get('FREQ') != 'YEARLY' or p.get('BYMONTH'):
        return None
    if not (p.get('BYWEEKNO') or p.get('BYYEARDAY')):
        return None
    interval = int(p.get('INTERVAL', 1))
    if p.get('BYDAY'):
        offs = []
        for t in p['BYDAY'].split(','):
            if t[-2:] not in DAYMAP:
                return None
            offs.append(DAYMAP[t[-2:]])
    else:
        offs = [1] if p.get('BYWEEKNO') else [1, 2, 3, 4, 5, 6, 7]
    weekno = p.get('BYWEEKNO')
    nums = [int(x) for x in (weekno or p['BYYEARDAY']).split(',')]
    count = int(p['COUNT']) if p.get('COUNT') else None
    until = p.get('UNTIL')
    if until:
        until = until.rstrip('Z')
        if 'T' not in until:
            until += 'T000000'
    cur = datetime.strptime(c['dtstart'], FMT).date()
    tod = c['dtstart'][8:]
    cap = c['limit'] if count is None else min(c['limit'], count)
    out = [c['dtstart']]
    for _ in range(cap * 3):
        if len(out) >= cap:
            break
        if cur.month == 2 and cur.day == 29:          # (a) the absorbing guard
            n = 0
            while True:
                n += 1
                nxt = php_add_years(cur, interval * n)
                if nxt.month == 2:
                    break
                if n > 40:
                    return None
            cur = nxt
        else:
            y, found = cur.year, None
            for _ in range(200):
                cands = []
                for v in nums:
                    if weekno:
                        for d in offs:
                            try:
                                x = iso_setdate(y, v, d)
                            except (ValueError, OverflowError):
                                continue
                            if x > cur:
                                cands.append(x)
                    else:
                        try:
                            x = (date(y, 1, 1) + timedelta(days=v - 1) if v > 0
                                 else date(y, 12, 31) - timedelta(days=abs(v + 1)))
                        except (ValueError, OverflowError):
                            continue
                        if x > cur and x.isoweekday() in offs:   # (b)
                            cands.append(x)
                if cands:
                    found = min(cands); break
                y += interval
            if found is None:
                return None
            cur = found
        s = cur.strftime("%Y%m%d") + tod
        if until and s > until:
            break
        out.append(s)
    return out[:cap]



# ------------------------------------------------------------- mechanism 6/7
#
# The two mechanisms below were added by finding 086.  Everything above models
# sabre by DELETING what a code path does not read; that is a rewrite, and a
# rewrite is only as good as the assumption that what IS read is then handled
# correctly.  For two branches it is not, so these two SIMULATE the branch
# statement for statement instead of rewriting the rule.  They are narrower
# than the deletion models -- each answers only for one branch of one method --
# and so they run first.

def php_w(d):
    """PHP format('w'): Sunday=0 .. Saturday=6, which is also $dayMap."""
    return d.isoweekday() % 7


def php_setdate(dt, y, m, day):
    """PHP DateTime::setDate(), which does NOT reject an out-of-range day: it
    overflows into the following month.  setDate(2026, 2, 29) is 2026-03-01."""
    base = date(y, m, 1) + timedelta(days=day - 1)
    return dt.replace(year=base.year, month=base.month, day=base.day)


def _cap(c, p):
    n = c['limit']
    if p.get('COUNT'):
        n = min(n, int(p['COUNT']))
    return n


def _until(p):
    u = p.get('UNTIL')
    if not u:
        return None
    u = u.rstrip('Z')
    return u if 'T' in u else u + 'T000000'


def _run(c, p, step):
    """The iterator yields DTSTART first, then repeats step()."""
    cur = datetime.strptime(c['dtstart'], FMT)
    st = cur.time()
    cap, until = _cap(c, p), _until(p)
    out = [cur.strftime(FMT)]
    for _ in range(cap * 4):
        if len(out) >= cap:
            break
        cur = step(cur, st)
        if cur is None:
            return None
        s = cur.strftime(FMT)
        if until and s > until:
            break
        out.append(s)
    return out[:cap]


def weekly_hour_walk(c):
    """nextWeekly() with BYHOUR advances the clock by ONE HOUR, not one week.

        do {
            if ($this->byHour) { $this->currentDate = ...modify('+1 hours'); }
            else               { $this->advanceTheDate('+1 days'); }
            ...
            if ($currentDay === $firstDay && (!$this->byHour || '0' == $currentHour)) {
                $this->currentDate = ...modify('+'.($this->interval - 1).' weeks');
                ...
            }
        } while ((byDay && !in_array(currentDay, days)) || (byHour && !in_array(currentHour, hours)));

    The week rollover -- the only place INTERVAL and WKST are consulted -- can
    only fire at hour 0 of the first day of the week, and at INTERVAL=1 it is a
    no-op.  Nothing else in the loop is weekly.  So FREQ=WEEKLY;BYHOUR=9 is not
    9 o'clock once a week: it is 9 o'clock EVERY DAY, and the frequency the
    caller asked for has been silently replaced by a denser one.  That is the
    opposite direction from every other defect here, which drop occurrences.

    BYSETPOS is not read at WEEKLY at all, which is why deleting it (mechanism
    1) was right about the rule and still wrong about the answer."""
    p = parts(c['rrule'])
    if p.get('FREQ') != 'WEEKLY' or not p.get('BYHOUR'):
        return None
    interval = int(p.get('INTERVAL', 1))
    try:
        hours = [int(x) for x in p['BYHOUR'].split(',')]
        days = [DAYMAP[t[-2:]] for t in p['BYDAY'].split(',')] if p.get('BYDAY') else []
    except (KeyError, ValueError):
        return None
    if p.get('WKST') and p['WKST'] not in DAYMAP:
        return None
    first = DAYMAP[p.get('WKST', 'MO')]

    def step(cur, st):
        for _ in range(24 * 366 * 5):
            cur = cur + timedelta(hours=1)
            cday, chour = php_w(cur), cur.hour
            if cday == first and chour == 0:
                cur = cur + timedelta(weeks=interval - 1)
                if php_w(cur) != first:                  # modify('last <day>')
                    cur = cur - timedelta(days=((php_w(cur) - first) % 7) or 7)
            if (days and cday not in days) or chour not in hours:
                continue
            return cur
        return None
    return _run(c, p, step)


def monthly_occurrences(cur, p):
    """getMonthlyOccurrences(), for the month $currentDate is in.  Returns day
    numbers.  Note where BYSETPOS is applied: INSIDE this, i.e. per MONTH."""
    y, m = cur.year, cur.month
    ndays = (date(y + (m == 12), (m % 12) + 1, 1) - timedelta(days=1)).day
    byday = []
    if p.get('BYDAY'):
        for tok in p['BYDAY'].split(','):
            if tok[-2:] not in DAYMAP:
                return None
            hits = [d for d in range(1, ndays + 1)
                    if php_w(date(y, m, d)) == DAYMAP[tok[-2:]]]
            if len(tok) > 2:
                off = int(tok[:-2])
                i = off - 1 if off > 0 else len(hits) + off
                if 0 <= i < len(hits):
                    byday.append(hits[i])
            else:
                byday += hits
    bymd = []
    if p.get('BYMONTHDAY'):
        for v in (int(x) for x in p['BYMONTHDAY'].split(',')):
            if v > ndays or v < -ndays:
                continue
            bymd.append(v if v > 0 else ndays + 1 + v)
    if p.get('BYMONTHDAY') and p.get('BYDAY'):
        res = [x for x in bymd if x in byday]
    elif p.get('BYMONTHDAY'):
        res = bymd
    else:
        res = byday
    res = sorted(set(res))
    if not p.get('BYSETPOS'):
        return res
    filt = []
    for sp in (int(x) for x in p['BYSETPOS'].split(',')):
        i = len(res) + sp if sp < 0 else sp - 1
        if 0 <= i < len(res):
            filt.append(res[i])
    return sorted(set(filt))


def yearly_bymonth_walk(c):
    """nextYearly()'s BYMONTH branch, simulated rather than rewritten.

    Two sub-branches, and the deletion model is wrong about both:

    (a) NO BYDAY AND NO BYMONTHDAY.  The method walks the month number forward
        to the next member of BYMONTH (adding INTERVAL to the year when it
        passes December) and then calls setDate() with THE DAY NUMBER IT
        ALREADY HAD.  BYSETPOS and BYMONTHDAY are never read on this path, and
        PHP's setDate() overflows rather than rejecting, so a 29 or a 31 landing
        in a short month moves the series permanently: FREQ=YEARLY;INTERVAL=2;
        BYMONTH=2 from 2024-02-29 gives 2026-03-01 -- and then the day number
        for every later occurrence is 1.

    (b) BYDAY OR BYMONTHDAY PRESENT.  getMonthlyOccurrences() is called for ONE
        month and BYSETPOS is applied inside it, so BYSETPOS selects within the
        month rather than within the year, which is what RFC 5545 3.3.10 asks
        for at FREQ=YEARLY.  The first occurrence strictly greater than the
        current day of the month wins (any occurrence, once the walk has moved
        to a new month)."""
    p = parts(c['rrule'])
    if p.get('FREQ') != 'YEARLY' or not p.get('BYMONTH'):
        return None
    interval = int(p.get('INTERVAL', 1))
    months = [int(x) for x in p['BYMONTH'].split(',')]
    if not months:
        return None
    expands = bool(p.get('BYDAY') or p.get('BYMONTHDAY'))

    def next_month(y, m):
        for _ in range(12 * 40):
            m += 1
            if m > 12:
                y += interval
                m = 1
            if m in months:
                return y, m
        return None, None

    def step(cur, st):
        m, y, dom = cur.month, cur.year, cur.day
        if not expands:
            y, m = next_month(y, m)
            if y is None:
                return None
            return php_setdate(cur, y, m, dom).replace(
                hour=st.hour, minute=st.minute, second=st.second)
        advanced, tmp = False, cur
        for _ in range(400):
            occs = monthly_occurrences(tmp, p)
            if occs is None:
                return None
            hit = None
            for o in occs:
                if (o > dom or advanced) and m in months:
                    hit = o
                    break
            if hit is not None:
                return php_setdate(tmp, y, m, hit).replace(
                    hour=st.hour, minute=st.minute, second=st.second)
            dom, advanced = 1, True
            y, m = next_month(y, m)
            if y is None or y > 9999:
                return None
            tmp = php_setdate(tmp, y, m, 1)
        return None
    return _run(c, p, step)


# --------------------------------------------------------------- the ordering
def predictors(c):
    """Narrowest first (standing rule 49)."""
    yield "086-E  WEEKLY: BYHOUR makes the loop walk hours, not weeks", weekly_hour_walk(c)
    yield "086-D  YEARLY: the BYMONTH month-walk (day carried, BYSETPOS per month)", yearly_bymonth_walk(c)
    yield "076-C  MINUTELY/SECONDLY: the date is never advanced", never_advances(c)
    yield "076-B  YEARLY: leap-day guard + off-by-one weekday index", yearly_no_bymonth(c)
    yield "076-A  DAILY: the no-BYHOUR/no-BYDAY early return skips BYMONTH", daily_fast_path(c)
    yield "031/076  BY parts the FREQ method never reads", unread_parts(c)


def attribute(c, got):
    for name, pred in predictors(c):
        if pred is not None and pred == got:
            return name
    return None


def main():
    dump = json.load(open(sys.argv[1]))
    verify = '--verify' in sys.argv
    rows = [f for f in dump['failures'] if f['bucket'] == 'fail']
    hits = collections.Counter(); who = collections.defaultdict(list)
    for f in rows:
        c = f['case']; got = (f['reply'] or {}).get('occurrences')
        if got is None:
            label = 'NO REPLY'
        else:
            label = attribute(c, got) or 'unexplained'
        hits[label] += 1; who[label].append(c['id'])
    print("scored %d mismatches against %s"
          % (len(rows), dump['corpus_version']['cases_id'][:12]))
    for k, v in hits.most_common():
        print("%5d  %s" % (v, k))

    fp = None
    if verify:
        # Two-sided check (standing rule 82).  Deleting a BY part can only
        # LOOSEN a rule, so a deletion model is wrong in the direction of
        # claiming cases where the deleted part happened not to matter.  On
        # every case sabre PASSED, no mechanism above may claim a different
        # answer than the one sabre actually gave.
        failed = {f['case']['id'] for f in dump['failures']}
        fp = []; n = 0
        for line in open("conformance/cases.ndjson"):
            c = json.loads(line)
            if c['id'] in failed:
                continue
            n += 1
            if attribute(c, c['expect']) is None:
                for name, pred in predictors(c):
                    if pred is not None and pred != c['expect']:
                        fp.append({"id": c['id'], "rrule": c['rrule'],
                                   "dtstart": c['dtstart'], "mechanism": name})
                        break
        print("\nverify: %d passed cases replayed, %d of them would have been "
              "broken by a mechanism above" % (n, len(fp)))
        for r in fp[:12]:
            print("   %s  %s  %s  <- %s"
                  % (r['id'][:8], r['rrule'], r['dtstart'], r['mechanism']))

    out = {"cases_id": dump['corpus_version']['cases_id'],
           "counts": dump['counts'], "attribution": dict(hits), "ids": dict(who)}
    if fp is not None:
        out["verify_false_positives"] = fp
    dest = os.path.join("findings", "data", "076-sabre-residual-reproduced.json")
    json.dump(out, open(dest, "w"), indent=1, sort_keys=True)
    print("\n-> %s" % dest)


if __name__ == "__main__":
    main()

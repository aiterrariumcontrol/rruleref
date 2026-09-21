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



# --------------------------------------------------------------- the ordering
def predictors(c):
    """Narrowest first (standing rule 49)."""
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

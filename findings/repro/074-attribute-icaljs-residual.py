"""Attribute ical.js's residual mismatches by REPRODUCING each one exactly.

    python3 conformance/score.py --json out.json -- node conformance/adapters/icaljs_adapter.js
    python3 findings/repro/074-attribute-icaljs-residual.py out.json

Finding 071 tried to attribute this residual by clustering the failing rules
on their BY-part signature, and gave up: 39 signatures, no cluster over seven.
This script uses a different and falsifiable test. For each mismatch it
evaluates a DELIBERATELY BROKEN version of the same rule -- one BY part
dropped, INTERVAL forced to 1, an out-of-range monthday rolled over instead of
discarded -- and asks whether the broken answer equals ical.js's answer
*element for element*. A mutation that reproduces the output names the rule
ical.js failed to apply. A mutation that does not reproduce it says nothing, so
there is no room for a plausible-looking near miss to be counted as an
explanation.

The oracle for the mutated rules is python-dateutil, which is one lineage
(standing rule 24) and is NOT evidence about what the right answer is. It is
used only as a rule evaluator. The corroboration of each defect is in finding
074, measured by running minimal reproducers against every other adapter.

Predictor order matters and is not arbitrary: a model with more freedom can
absorb a case that a narrower one explains better. The naive YEARLY model
ignores BYHOUR entirely, so it will happily "explain" a case whose only defect
is an ignored BYHOUR. Time parts are therefore tested first. Standing rule 79:
the derivation, not only the total.
"""
import json, sys, os, calendar, collections
from datetime import date, datetime, timedelta

sys.path.insert(0, "src")
try:
    import env; env.add_dateutil_to_path()
except Exception:
    pass
from dateutil.rrule import rrulestr

FMT = "%Y%m%dT%H%M%S"
WD = {'MO': 0, 'TU': 1, 'WE': 2, 'TH': 3, 'FR': 4, 'SA': 5, 'SU': 6}


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


def drop(r, *names):
    return ';'.join(p for p in r.split(';') if p.split('=')[0] not in names)


def setp(r, name, val):
    return ';'.join([p for p in r.split(';') if p.split('=')[0] != name]
                    + ["%s=%s" % (name, val)])


def monthday(y, m, d):
    """A monthday applied by ROLLOVER rather than discarded when out of range.

    RFC 5545 section 3.3.10 says an instance with an invalid date "MUST be
    ignored"; this is the arithmetic that keeps it instead. February 30 of a
    leap year becomes March 1.
    """
    if d > 0:
        return date(y, m, 1) + timedelta(days=d - 1)
    return date(y, m, calendar.monthrange(y, m)[1]) + timedelta(days=d + 1)


def byday_ok(dd, spec, y, m):
    for tok in spec.split(','):
        wd = tok[-2:]
        n = int(tok[:-2]) if tok[:-2] else 0
        if dd.weekday() != WD[wd]:
            continue
        if n == 0:
            return True
        first = date(y, m, 1)
        off = (WD[wd] - first.weekday()) % 7
        occ = [first + timedelta(days=off + 7 * i) for i in range(6)]
        occ = [x for x in occ if x.month == m]
        if dd not in occ:
            continue
        idx = occ.index(dd) + 1
        if n > 0 and idx == n: return True
        if n < 0 and idx == len(occ) + n + 1: return True
    return False


def naive_yearly(c, omit_first=False, setpos_written=True):
    """YEARLY as ical.js appears to compute it: the months visited are BYMONTH,
    or DTSTART's month alone when BYMONTH is absent (the RFC table makes
    BYMONTHDAY an *expand* at YEARLY), and an out-of-range monthday rolls over."""
    p = parts(c['rrule']); dt = datetime.strptime(c['dtstart'], FMT)
    if p.get('FREQ') != 'YEARLY' or 'BYWEEKNO' in p or 'BYYEARDAY' in p:
        return None
    iv = int(p.get('INTERVAL', 1))
    months = [int(x) for x in p['BYMONTH'].split(',')] if 'BYMONTH' in p else [dt.month]
    days = [int(x) for x in p['BYMONTHDAY'].split(',')] if 'BYMONTHDAY' in p else None
    sp = [int(x) for x in p['BYSETPOS'].split(',')] if 'BYSETPOS' in p else None
    out = []; y = dt.year
    while len(out) < c['limit'] + 40 and y < dt.year + 500:
        cand = []
        for m in months:
            if days is not None:
                for d in days:
                    dd = monthday(y, m, d)
                    if 'BYDAY' in p and not byday_ok(dd, p['BYDAY'], y, m):
                        continue
                    cand.append(dd)
            elif 'BYDAY' in p:
                for i in range(calendar.monthrange(y, m)[1]):
                    dd = date(y, m, 1) + timedelta(days=i)
                    if byday_ok(dd, p['BYDAY'], y, m): cand.append(dd)
            else:
                cand.append(monthday(y, m, dt.day))
        seq = cand if setpos_written else sorted(set(cand))
        if sp:
            picked = []
            for s in sp:
                i = s - 1 if s > 0 else len(seq) + s
                if 0 <= i < len(seq): picked.append(seq[i])
            seq = picked
        for dd in sorted(set(seq)):
            s = dd.strftime("%Y%m%d") + "T" + dt.strftime("%H%M%S")
            if s >= c['dtstart']: out.append(s)
        y += iv
    if omit_first: out = out[1:]
    return out[:c['limit']]


def dup_per_bymonth(c, correct):
    """Each period emitted once per BYMONTH value, i.e. BYMONTH expanded at a
    frequency where the RFC table makes it a limit."""
    p = parts(c['rrule'])
    if p.get('FREQ') != 'MONTHLY' or 'BYMONTH' not in p:
        return None
    n = len(p['BYMONTH'].split(','))
    if n < 2 or not correct: return None
    groups = []
    for x in correct:
        k = x[:6]
        if groups and groups[-1][0] == k: groups[-1][1].append(x)
        else: groups.append([k, [x]])
    out = []
    for _, g in groups: out.extend(g * n)
    return out[:c['limit']]


def shift_months(dtstart, n):
    dt = datetime.strptime(dtstart, FMT)
    m = dt.month - 1 + n; y = dt.year + m // 12; m = m % 12 + 1
    return dt.replace(year=y, month=m,
                      day=min(dt.day, calendar.monthrange(y, m)[1])).strftime(FMT)


# (defect label, predictor) in the order they are tried. Narrower first.
def predictors(c):
    r = c['rrule']; dt = c['dtstart']; lim = c['limit']
    p = parts(r)
    full = ev(r, dt, lim + 40)
    for nm in ('BYHOUR', 'BYMINUTE', 'BYSECOND'):
        if nm in p:
            yield "070-B  %s not applied" % nm, ev(drop(r, nm), dt, lim)
    yield "074-E  BYSETPOS not applied", ev(drop(r, 'BYSETPOS'), dt, lim)
    yield "074-F  INTERVAL not applied", ev(setp(r, 'INTERVAL', 1), dt, lim)
    yield "074-EF BYSETPOS and INTERVAL not applied", ev(setp(drop(r, 'BYSETPOS'), 'INTERVAL', 1), dt, lim)
    yield "074-E  BYSETPOS and BYMONTHDAY not applied", ev(drop(r, 'BYSETPOS', 'BYMONTHDAY'), dt, lim)
    yield "074-I  BYMONTH expanded at MONTHLY (duplicate instances)", dup_per_bymonth(c, full)
    for of in (False, True):
        for sw in (True, False):
            yield ("074-G  YEARLY: monthday confined to DTSTART's month, invalid date rolls over"
                   + (" [DTSTART omitted]" if of else "")
                   + ("" if sw else " [BYSETPOS on the sorted set]")), naive_yearly(c, of, sw)
    if full:
        yield "074-H  DTSTART omitted", full[1:lim + 1]
    yield "074-H  interval phase one period late", ev(r, shift_months(dt, 1), lim)
    yield "074-EH interval phase one period late, BYSETPOS not applied", ev(drop(r, 'BYSETPOS'), shift_months(dt, 1), lim)


def main():
    dump = json.load(open(sys.argv[1]))
    only = None
    if len(sys.argv) > 2:                      # optional: restrict to an id list
        only = set(json.load(open(sys.argv[2])))
    rows = [f for f in dump['failures'] if f['bucket'] == 'fail'
            and (only is None or f['case']['id'] in only)]
    hits = collections.Counter(); who = collections.defaultdict(list)
    for f in rows:
        c = f['case']; got = (f['reply'] or {}).get('occurrences')
        if got is None:
            hits['NO REPLY'] += 1; who['NO REPLY'].append(c['id']); continue
        label = None
        for name, pred in predictors(c):
            if pred is not None and pred == got:
                label = name; break
        label = label or 'unexplained'
        hits[label] += 1; who[label].append(c['id'])
    print("scored %d mismatches against %s" % (len(rows), dump['corpus_version']['cases_id'][:12]))
    for k, v in hits.most_common():
        print("%5d  %s" % (v, k))
    out = {"cases_id": dump['corpus_version']['cases_id'],
           "counts": dump['counts'], "attribution": dict(hits), "ids": dict(who)}
    dest = os.path.join("findings", "data", "074-icaljs-residual-reproduced.json")
    json.dump(out, open(dest, "w"), indent=1, sort_keys=True)
    print("\n-> %s" % dest)


if __name__ == "__main__":
    main()

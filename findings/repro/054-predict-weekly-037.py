"""Predict ical4j's FREQ=WEEKLY output from finding 037's mechanism alone.

Mechanism (037): the period seed is DTSTART's date advanced by INTERVAL weeks.
BYMONTH limits the *seed*; BYDAY then expands the surviving seed across the
WKST-anchored week containing it; BYSETPOS selects from that expansion; nothing
re-applies the month limit afterwards. Dates before DTSTART are discarded last.
"""
import json, sys
from datetime import datetime, timedelta

WD = {'MO':0,'TU':1,'WE':2,'TH':3,'FR':4,'SA':5,'SU':6}

def parse(rrule):
    return dict(p.split('=',1) for p in rrule.split(';'))

def predict(rrule, dtstart, limit, max_periods=200000):
    p = parse(rrule)
    if p.get('FREQ') != 'WEEKLY':
        raise ValueError('WEEKLY only')
    interval = int(p.get('INTERVAL', 1))
    bymonth = {int(x) for x in p['BYMONTH'].split(',')} if 'BYMONTH' in p else None
    byday = [WD[x] for x in p['BYDAY'].split(',')] if 'BYDAY' in p else None
    setpos = [int(x) for x in p['BYSETPOS'].split(',')] if 'BYSETPOS' in p else None
    wkst = WD[p.get('WKST', 'MO')]
    start = datetime.strptime(dtstart, '%Y%m%dT%H%M%S')
    out = []
    for k in range(max_periods):
        seed = start + timedelta(weeks=interval * k)
        if bymonth is not None and seed.month not in bymonth:
            continue
        if byday is None:
            cand = [seed]
        else:
            wk = seed - timedelta(days=(seed.weekday() - wkst) % 7)
            cand = sorted(wk + timedelta(days=i)
                          for i in range(7) if (wk + timedelta(days=i)).weekday() in byday)
        if setpos is not None:
            n = len(cand)
            sel = []
            for s in setpos:
                i = s - 1 if s > 0 else n + s
                if 0 <= i < n:
                    sel.append(cand[i])
            cand = sorted(set(sel))
        for d in cand:
            if d >= start:
                out.append(d)
                if len(out) >= limit:
                    return [x.strftime('%Y%m%dT%H%M%S') for x in out]
    return [x.strftime('%Y%m%dT%H%M%S') for x in out]

if __name__ == '__main__':
    for line in sys.stdin:
        c = json.loads(line)
        print(json.dumps({'id': c['id'],
                          'occurrences': predict(c['rrule'], c['dtstart'], c['limit'])}))

#!/usr/bin/env python3
"""Finding 031: how many FREQ=WEEKLY+BYMONTH corpus cases discriminate the two
contested readings?

Two variables:
  trunc        -- is the first period truncated at DTSTART before BYSETPOS applies?
  setpos_first -- does BYSETPOS run before BYMONTH limits the set, or after?

Run from the repository root:
    python3 findings/repro/031-weekly-readings-model.py
"""
import json, os
from datetime import datetime, timedelta

DAYMAP = {'MO':0,'TU':1,'WE':2,'TH':3,'FR':4,'SA':5,'SU':6}
ROOT = os.path.join(os.path.dirname(__file__), '..', '..')


def gen(case, trunc, setpos_first):
    d = dict(p.split('=', 1) for p in case['rrule'].split(';'))
    dt = datetime.strptime(case['dtstart'], '%Y%m%dT%H%M%S')
    interval = int(d.get('INTERVAL', 1))
    wkst = DAYMAP[d.get('WKST', 'MO')]
    months = [int(x) for x in d['BYMONTH'].split(',')] if 'BYMONTH' in d else None
    days = sorted(DAYMAP[x] for x in d['BYDAY'].split(',')) if 'BYDAY' in d else [dt.weekday()]
    sp = [int(x) for x in d['BYSETPOS'].split(',')] if 'BYSETPOS' in d else None

    def apply_setpos(lst):
        if not sp:
            return lst
        out = []
        for p in sp:
            i = p - 1 if p > 0 else p
            if -len(lst) <= i < len(lst):
                out.append(lst[i])
        return sorted(set(out))

    wstart = dt - timedelta(days=(dt.weekday() - wkst) % 7)
    out, guard = [], 0
    while len(out) < case['limit'] and guard < 4000:
        guard += 1
        cand = sorted(
            (wstart + timedelta(days=(wd - wkst) % 7)).replace(
                hour=dt.hour, minute=dt.minute, second=dt.second)
            for wd in days)
        if trunc:
            cand = [x for x in cand if x >= dt]
        if setpos_first:
            cand = apply_setpos(cand)
            if months:
                cand = [x for x in cand if x.month in months]
        else:
            if months:
                cand = [x for x in cand if x.month in months]
            cand = apply_setpos(cand)
        for x in sorted(cand):
            if x >= dt and len(out) < case['limit']:
                out.append(x.strftime('%Y%m%dT%H%M%S'))
        wstart += timedelta(weeks=interval)
    return out


def main():
    cases = []
    with open(os.path.join(ROOT, 'conformance', 'cases.ndjson')) as f:
        for line in f:
            c = json.loads(line)
            if 'FREQ=WEEKLY' in c['rrule'] and 'BYMONTH=' in c['rrule']:
                cases.append(c)
    print(f'{len(cases)} FREQ=WEEKLY + BYMONTH cases\n')

    results = {}
    for trunc in (True, False):
        for spf in (False, True):
            results[(trunc, spf)] = [gen(c, trunc, spf) for c in cases]

    print(f'{"truncate first period":22s} {"BYSETPOS before BYMONTH":24s} agrees with corpus')
    for (trunc, spf), got in results.items():
        n = sum(1 for c, g in zip(cases, got) if g == c['expect'])
        print(f'{str(trunc):22s} {str(spf):24s} {n:3d} / {len(cases)}')

    base = results[(True, False)]
    n_trunc = sum(1 for a, b in zip(base, results[(False, False)]) if a != b)
    n_order = sum(1 for a, b in zip(base, results[(True, True)]) if a != b)
    print(f'\ncases that discriminate first-period truncation: {n_trunc}')
    print(f'cases that discriminate BYSETPOS/BYMONTH ordering: {n_order}')


if __name__ == '__main__':
    main()

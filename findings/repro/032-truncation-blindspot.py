#!/usr/bin/env python3
"""Finding 032: the corpus cannot contain a case that discriminates first-period
truncation at FREQ=WEEKLY, because its two adjudicators sit on opposite sides
of the question.

No harness, no corpus, no adapters. Needs only python-dateutil (it will
fall back to the copy vendored under vendor/pylibs if none is installed).

    python3 findings/repro/032-truncation-blindspot.py
"""
import itertools, random, datetime, os, sys

try:
    from dateutil import rrule as du
except ImportError:  # fall back to the copy vendored in this repository
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', '..', 'vendor', 'pylibs'))
    from dateutil import rrule as du

DAYMAP = {'MO': 0, 'TU': 1, 'WE': 2, 'TH': 3, 'FR': 4, 'SA': 5, 'SU': 6}
DAYS = list(DAYMAP)
BASE = datetime.datetime(2026, 1, 5, 9, 0, 0)   # a Monday


def reading(rrule, dt, limit, truncate):
    """Expand FREQ=WEEKLY with BYSETPOS under one of the two contested readings.

    truncate=True   the first interval's candidate set is cut at DTSTART before
                    BYSETPOS indexes it   (python-dateutil's behaviour)
    truncate=False  the candidate set is the whole week, per RFC 5545 3.3.10
                    "A set of recurrence instances starts at the beginning of
                    the interval defined by the FREQ rule part."
    """
    d = dict(p.split('=', 1) for p in rrule.split(';'))
    interval = int(d.get('INTERVAL', 1))
    wkst = DAYMAP[d.get('WKST', 'MO')]
    months = [int(x) for x in d['BYMONTH'].split(',')] if 'BYMONTH' in d else None
    days = sorted(DAYMAP[x] for x in d['BYDAY'].split(','))
    sp = [int(x) for x in d['BYSETPOS'].split(',')]

    wstart = dt - datetime.timedelta(days=(dt.weekday() - wkst) % 7)
    out, guard = [], 0
    while len(out) < limit and guard < 4000:
        guard += 1
        cand = sorted((wstart + datetime.timedelta(days=(wd - wkst) % 7)).replace(
            hour=dt.hour, minute=dt.minute, second=dt.second) for wd in days)
        if truncate:
            cand = [x for x in cand if x >= dt]
        if months:                       # BYSETPOS is applied last (3.3.10)
            cand = [x for x in cand if x.month in months]
        picked = []
        for p in sp:
            i = p - 1 if p > 0 else p
            if -len(cand) <= i < len(cand):
                picked.append(cand[i])
        for x in sorted(set(picked)):
            if x >= dt and len(out) < limit:
                out.append(x)
        wstart += datetime.timedelta(weeks=interval)
    return out


def dateutil_expand(rrule, dt, limit):
    try:
        return list(itertools.islice(iter(du.rrulestr("RRULE:" + rrule, dtstart=dt)), limit))
    except Exception as e:
        return "ERROR:" + type(e).__name__


def main():
    combos = []
    for ndays in (2, 3, 4):
        for byday in itertools.combinations(DAYS, ndays):
            for sp in ('1', '2', '-1', '1,-1'):
                for months in (None, '1', '1,3', '2'):
                    for off in range(7):
                        parts = ['FREQ=WEEKLY', 'BYDAY=' + ','.join(byday)]
                        if months:
                            parts.append('BYMONTH=' + months)
                        parts.append('BYSETPOS=' + sp)
                        combos.append((';'.join(parts),
                                       BASE + datetime.timedelta(days=off)))
    random.seed(11)
    random.shuffle(combos)
    sample = combos[:800]

    du_trunc = du_full = 0
    tab = {}
    for r, dt in sample:
        t = reading(r, dt, 8, True)
        f = reading(r, dt, 8, False)
        got = dateutil_expand(r, dt, 8)
        du_trunc += got == t
        du_full += got == f
        # The corpus admits a case only when its two expanders agree. The
        # spec-derived one implements the untruncated reading, so "the
        # adjudicators disagree" is exactly "dateutil != untruncated".
        tab[(t != f, got != f)] = tab.get((t != f, got != f), 0) + 1

    n = len(sample)
    print(f"sample of {n} FREQ=WEEKLY rules with BYSETPOS\n")
    print(f"  python-dateutil matches the truncated reading   : {du_trunc}/{n}")
    print(f"  python-dateutil matches the untruncated reading : {du_full}/{n}")
    print(f"\n  {'readings differ':18s} {'adjudicators disagree':22s} n")
    for k in sorted(tab):
        print(f"  {str(k[0]):18s} {str(k[1]):22s} {tab[k]}")
    off_diagonal = sum(v for k, v in tab.items() if k[0] != k[1])
    print(f"\n  off-diagonal: {off_diagonal}")
    print("\nA case discriminates the truncation question if and only if the two\n"
          "adjudicators disagree on it -- so it is routed to disputed.json and\n"
          "can never enter the corpus. The blind spot is structural.")


if __name__ == '__main__':
    main()

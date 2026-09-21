"""Attribute ical4j's residual mismatches by REPRODUCING each one exactly.

    CP="conformance/adapters/java/classes:$(ls conformance/adapters/java/libs/*.jar | tr '\n' ':')"
    TZ=UTC python3 conformance/score.py --json out.json -- \
        java -Duser.language=en -Duser.country=US -cp "$CP" Ical4jAdapter
    python3 findings/repro/075-attribute-ical4j-residual.py out.json

Finding 051 accounted for this residual by sorting the failing rules into six
categories, and said so in the open: "Categories C, E and F are assigned by rule
*shape*, not by a verified cause." Standing rule 81 -- which finding 074
arrived at afterwards -- says that is a guess. This script re-does the
attribution the way 074 did ical.js's: each mismatch is predicted, element for
element, from a stated defect, and a prediction that misses explains nothing.

The oracle is python-dateutil, used ONLY as a rule evaluator (standing rule 24);
it is not evidence about the right answer. Four mechanisms are tried:

  1. LOCALE WEEK       the week starts on the JVM locale's first day of week
                       rather than on WKST (finding 036).
  2. SEED LIMIT        a limiting BY part is tested against the period's seed
                       date and then not applied to the set the period expands
                       to (finding 037, generalised past FREQ=WEEKLY).
  3. NEGATIVE LIMIT    a negative value in a limiting BY part never matches
                       (findings 049/050, generalised past BYMONTHDAY).
  4. NO DEDUPLICATION  two BY values naming the same instant emit it twice
                       (finding 051 defect A).

Mechanism 3 usually predicts an EMPTY list, and an empty prediction is cheap:
almost any broken rule can produce one. The two-sided check in --verify is what
makes it a measurement. It replays the model over EVERY case in the corpus,
including the ones ical4j passes, and requires the model to agree with ical4j
there too -- so a mechanism that emptied lists it should not have emptied is
caught by the cases it would have had to break and did not.
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
LIMITING = {                      # BY part -> the FREQ values at which it limits
    'BYMONTH':    {'WEEKLY', 'DAILY', 'HOURLY', 'MINUTELY', 'SECONDLY'},
    'BYMONTHDAY': {'DAILY', 'HOURLY', 'MINUTELY', 'SECONDLY'},
    'BYYEARDAY':  {'DAILY', 'HOURLY', 'MINUTELY', 'SECONDLY'},
    'BYDAY':      {'DAILY', 'HOURLY', 'MINUTELY', 'SECONDLY'},
}


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


def is_negative(part, tok):
    """Is this BY token's value negative? BYDAY's sign lives in its ordinal."""
    if part != 'BYDAY':
        return tok.startswith('-')
    return tok[:-2].startswith('-')


# ---------------------------------------------------------------- mechanism 3
def negative_limit(c):
    """A negative value in a LIMITING BY part never matches.

    Every value negative -> the limit can never be satisfied and the answer is
    empty. Some values positive -> the rule with the negative ones deleted.
    """
    p = parts(c['rrule']); freq = p.get('FREQ')
    r = c['rrule']; touched = False
    for part, freqs in LIMITING.items():
        if part not in p or freq not in freqs:
            continue
        toks = p[part].split(',')
        keep = [t for t in toks if not is_negative(part, t)]
        if len(keep) == len(toks):
            continue
        touched = True
        if not keep:
            return []
        r = setp(r, part, ','.join(keep))
    if not touched:
        return None
    return ev(r, c['dtstart'], c['limit'])


def ordinal_byday_limit(c):
    """An ORDINAL BYDAY in its limiting role never matches (finding 051 B).

    BYDAY limits rather than expands when BYMONTHDAY or BYYEARDAY is present at
    MONTHLY or YEARLY. Every token ordinal -> empty; otherwise the plain ones.
    """
    p = parts(c['rrule'])
    if p.get('FREQ') not in ('MONTHLY', 'YEARLY') or 'BYDAY' not in p:
        return None
    if 'BYMONTHDAY' not in p and 'BYYEARDAY' not in p:
        return None
    toks = p['BYDAY'].split(',')
    keep = [t for t in toks if not t[:-2]]
    if len(keep) == len(toks):
        return None
    if not keep:
        return []
    return ev(setp(c['rrule'], 'BYDAY', ','.join(keep)), c['dtstart'], c['limit'])


# ---------------------------------------------------------------- mechanism 2
def seed_limit_dropped(c):
    """A limiting BY part tested on the seed and then not applied to the set.

    Expressed as a mutation: the limit is simply absent. This is the same claim
    as finding 037 made at FREQ=WEEKLY, and it is tried here at the frequencies
    where the expanded set can leave the seed's month or week.
    """
    p = parts(c['rrule'])
    if 'BYMONTH' not in p or p.get('FREQ') != 'YEARLY':
        return None
    if 'BYYEARDAY' not in p and 'BYWEEKNO' not in p:
        return None
    return ev(drop(c['rrule'], 'BYMONTH'), c['dtstart'], c['limit'])


def weekly_seed_model(c, wkst):
    """FREQ=WEEKLY as ical4j computes it.

    The seed walks DTSTART forward by INTERVAL weeks. The limiting BY parts are
    tested against THE SEED. If the seed passes, the whole week around it --
    a week that starts on `wkst`, not on the rule's WKST -- is expanded by
    BYDAY and emitted with no further filtering. That is mechanisms 1 and 2
    in one place, because at FREQ=WEEKLY they are the same code path.
    """
    p = parts(c['rrule']); dt = datetime.strptime(c['dtstart'], FMT)
    if p.get('FREQ') != 'WEEKLY':
        return None
    if {'BYHOUR', 'BYMINUTE', 'BYSECOND', 'BYWEEKNO', 'BYYEARDAY'} & set(p):
        return None
    iv = int(p.get('INTERVAL', 1))
    w = wkst if wkst is not None else WD[p.get('WKST', 'MO')]
    days = ([WD[t[-2:]] for t in p['BYDAY'].split(',')] if 'BYDAY' in p
            else [dt.weekday()])
    months = [int(x) for x in p['BYMONTH'].split(',')] if 'BYMONTH' in p else None
    mds = [int(x) for x in p['BYMONTHDAY'].split(',')] if 'BYMONTHDAY' in p else None
    sp = [int(x) for x in p['BYSETPOS'].split(',')] if 'BYSETPOS' in p else None

    def seed_ok(x):
        if months and x.month not in months:
            return False
        if mds is not None:
            last = calendar.monthrange(x.year, x.month)[1]
            if not any((v > 0 and x.day == v) or (v < 0 and x.day == last + 1 + v)
                       for v in mds):
                return False
        return True

    def setpos(seq):
        if not sp:
            return seq
        out = []
        for s in sp:
            i = s - 1 if s > 0 else len(seq) + s
            if 0 <= i < len(seq):
                out.append(seq[i])
        return out

    count = int(p['COUNT']) if 'COUNT' in p else None
    until = p.get('UNTIL')
    if until and until.endswith('Z'):
        until = until[:-1]
    cap = c['limit'] if count is None else min(c['limit'], count)
    d0 = dt.date(); out = []; i = 0
    while len(out) < cap and i < 6000:
        seed = d0 + timedelta(days=7 * iv * i); i += 1
        if not seed_ok(seed):
            continue
        ws = seed - timedelta(days=(seed.weekday() - w) % 7)
        cand = sorted(ws + timedelta(days=k) for k in range(7)
                      if (ws + timedelta(days=k)).weekday() in days)
        for x in setpos(cand):
            s = x.strftime("%Y%m%d") + "T" + dt.strftime("%H%M%S")
            if until is not None and s > until:
                return out
            if s >= c['dtstart'] and len(out) < cap:
                out.append(s)
    return out


# ---------------------------------------------------------------- mechanism 4
def can_collide(part, toks):
    """Could two values of this BY part ever name the same instant?

    A literal repeat obviously can. So can a positive and a negative value,
    which meet in months (or years) of the right length. Two distinct positive
    values cannot.
    """
    norm = [t if part == 'BYDAY' else str(int(t)) for t in toks]  # "+1" == "1"
    if len(set(norm)) < len(norm):
        return True
    if part in ('BYMONTH', 'BYSETPOS'):
        return False
    if part == 'BYDAY':
        # Two ordinals of the same weekday meet in a month with that many of it
        # -- 1MO and -4MO in a four-Monday month.
        wds = [t[-2:] for t in toks]
        if len(set(wds)) < len(wds):
            return True
    return (any(is_negative(part, t) for t in toks)
            and any(not is_negative(part, t) for t in toks))


def no_dedup(c):
    """Two BY values naming the same instant emit it twice.

    Expressed as a mutation: evaluate the rule once per value of the repeating
    BY part and merge the answers WITHOUT removing repeats. A correct expander
    would take the union; this takes the multiset.
    """
    p = parts(c['rrule'])
    best = None
    for part in ('BYMONTHDAY', 'BYYEARDAY', 'BYDAY', 'BYSETPOS', 'BYMONTH'):
        if part not in p:
            continue
        if 'BYSETPOS' in p and part != 'BYSETPOS':
            # Splitting another part would also re-scope BYSETPOS, which is a
            # second change and not the mechanism being tested. The --verify
            # replay caught this: it claimed six cases ical4j gets right.
            continue
        toks = p[part].split(',')
        if len(toks) < 2:
            continue
        if not can_collide(part, toks):
            # Two values that cannot name the same instant cannot produce a
            # duplicate, so the multiset and the union are the same list and
            # this mechanism has nothing to predict. Skipping them is what
            # makes the two-sided --verify replay affordable.
            continue
        merged = []
        for t in toks:
            one = ev(setp(c['rrule'], part, t), c['dtstart'], c['limit'])
            if one is None:
                merged = None; break
            merged.extend(one)
        if merged is None:
            continue
        cand = sorted(merged)[:c['limit']]
        if best is None:
            best = cand
    return best


# ---------------------------------------------------------------- mechanism 5
def chained_expansion(c, omit_first=False):
    """At FREQ=YEARLY two expanding BY parts CHAIN instead of intersecting.

    RFC 5545 3.3.10 expands BYYEARDAY, BYWEEKNO and BYMONTHDAY from the same
    yearly period, so two of them together name the days that satisfy BOTH.
    ical4j instead lets the first expansion choose a MONTH and re-expands
    BYMONTHDAY inside it -- so BYYEARDAY=200 (a day in July) plus
    BYMONTHDAY=15,-1 yields 15 July and 31 July, neither of which is day 200.
    BYSETPOS then selects from that chained set, one yearly period at a time.
    """
    p = parts(c['rrule'])
    if p.get('FREQ') != 'YEARLY' or 'BYMONTHDAY' not in p:
        return None
    if 'BYYEARDAY' not in p and 'BYWEEKNO' not in p:
        return None
    seeds = ev(drop(c['rrule'], 'BYMONTHDAY', 'BYSETPOS'), c['dtstart'],
               c['limit'] * 4 + 60)
    if seeds is None:
        return None
    days = [int(x) for x in p['BYMONTHDAY'].split(',')]
    sp = [int(x) for x in p['BYSETPOS'].split(',')] if 'BYSETPOS' in p else None
    per_year = collections.OrderedDict()
    seen = set()
    for s in seeds:
        y, m = int(s[:4]), int(s[4:6])
        if (y, m) in seen:
            continue
        seen.add((y, m))
        last = calendar.monthrange(y, m)[1]
        for v in days:
            d = v if v > 0 else last + 1 + v
            if 1 <= d <= last:
                per_year.setdefault(y, []).append(
                    "%04d%02d%02dT%s" % (y, m, d, c['dtstart'][9:]))
    out = []
    for y in sorted(per_year):
        seq = sorted(per_year[y])
        if sp:
            picked = []
            for v in sp:
                i = v - 1 if v > 0 else len(seq) + v
                if 0 <= i < len(seq):
                    picked.append(seq[i])
            seq = picked
        out.extend(seq)
    out = sorted(x for x in out if x >= c['dtstart'])
    if omit_first:
        out = out[1:]
    return out[:c['limit']]


# ---------------------------------------------------------------- the ordering
def predictors(c):
    """Narrowest first (standing rule 49): a model with more freedom will
    otherwise absorb a case a tighter one explains."""
    yield "051-A  no deduplication of the expanded set", no_dedup(c)
    yield "051-B  ordinal BYDAY in its limiting role never matches", ordinal_byday_limit(c)
    yield "049-   negative value in a limiting BY part never matches", negative_limit(c)
    yield "075-J  YEARLY: two expansions chained instead of intersected", chained_expansion(c)
    yield "075-J  YEARLY: two expansions chained [DTSTART omitted]", chained_expansion(c, True)
    yield "037-   limit tested on the seed, not on the expanded set", seed_limit_dropped(c)
    yield "037/036 WEEKLY: seed limit + locale week start", weekly_seed_model(c, 6)
    yield "037-   WEEKLY: seed limit, week start from WKST", weekly_seed_model(c, None)


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

    false_empty = None
    if verify:
        # Two-sided check: on every case ical4j PASSED, no mechanism above may
        # claim a different answer. A mechanism that fires there would be
        # predicting a failure that did not happen.
        failed = {f['case']['id'] for f in dump['failures']}
        false_empty = []
        n = 0
        for line in open("conformance/cases.ndjson"):
            c = json.loads(line)
            if c['id'] in failed:
                continue
            n += 1
            lab = attribute(c, c['expect'])
            if lab is None:                       # model disagrees with reality
                for name, pred in predictors(c):
                    if pred is not None and pred != c['expect']:
                        false_empty.append({"id": c['id'], "rrule": c['rrule'],
                                            "mechanism": name})
                        break
        print("\nverify: %d passed cases replayed, %d of them would have been "
              "broken by a mechanism above" % (n, len(false_empty)))
        for r in false_empty[:10]:
            print("   %s  %s  <- %s" % (r['id'][:8], r['rrule'], r['mechanism']))

    out = {"cases_id": dump['corpus_version']['cases_id'],
           "counts": dump['counts'], "attribution": dict(hits), "ids": dict(who)}
    if false_empty is not None:
        out["verify_false_positives"] = false_empty
    dest = os.path.join("findings", "data", "075-ical4j-residual-reproduced.json")
    json.dump(out, open(dest, "w"), indent=1, sort_keys=True)
    print("\n-> %s" % dest)


if __name__ == "__main__":
    main()

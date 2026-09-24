"""Attribute DateTime::Event::ICal's residual by REPRODUCING each case exactly.

    TZ=UTC python3 conformance/score.py --json out.json -- \
        perl conformance/adapters/perl/dtical_adapter.pl
    python3 findings/repro/079-dtical-decompose.py < conformance/cases.ndjson > expr.ndjson
    TZ=UTC perl findings/repro/079-eval-expr.pl < expr.ndjson > pred.ndjson
    python3 findings/repro/079-attribute-dtical-residual.py out.json expr.ndjson pred.ndjson

`DateTime::Event::ICal` is the last large undecomposed block on the board and
the only implementation whose source had never been opened here.  Method is
findings 074-076's under standing rule 81: a mismatch is accounted for only
when a stated mechanism predicts the EXACT list the library returned.

What is stated here is one claim about the whole library rather than a list of
per-shape defects: recur() does not evaluate an RRULE, it REWRITES it into a
fixed set-algebra expression over DateTime::Event::Recurrence primitives.
079-dtical-decompose.py builds that expression from the rule alone;
079-eval-expr.pl evaluates it WITHOUT loading DateTime::Event::ICal.  So a
reproduced case says something sharper than "defect D explains it": it says the
defect is in the rewrite, and locates it in a named branch of a named sub.

Standing rule 82's two-sided check is the load-bearing part, and here it is
unusually strong.  The model is not a loosening or a tightening of the rule; it
is a DIFFERENT rule.  So it has no systematic bias towards agreeing with the
library, and the replay over every case the library PASSES is a real test: on
those cases the library's output is the corpus's `expect`, and the model must
produce `expect` too or it is wrong.
"""
import json, sys, collections


def load_ndjson(p):
    out = {}
    for line in open(p):
        line = line.strip()
        if line:
            o = json.loads(line)
            out[o['id']] = o
    return out


def main(scored, exprf, predf):
    res = json.load(open(scored))
    exprs = load_ndjson(exprf)
    preds = load_ndjson(predf)
    cases = {}
    for line in open('conformance/cases.ndjson'):
        c = json.loads(line)
        cases[c['id']] = c

    failed = {f['case']['id']: f for f in res['failures']}
    passed = [i for i in cases if i not in failed]

    def pred_of(i):
        p = preds.get(i)
        if p is None:
            return ('missing', None)
        if 'skip' in p:
            return ('skip', p['skip'])
        if 'error' in p:
            return ('error', p['error'])
        return ('occ', p['occurrences'])

    def act_of(f):
        r = f['reply']
        if r is None:
            return ('missing', None)
        if 'error' in r:
            return ('error', r['error'])
        return ('occ', r.get('occurrences'))

    # ---- the failing side: does the model reproduce what the library returned?
    repro, unattr, skipped = [], [], []
    for i, f in failed.items():
        pk, pv = pred_of(i)
        ak, av = act_of(f)
        if pk == 'skip':
            skipped.append((i, pv))
            continue
        if pk == 'occ' and ak == 'occ' and pv == av:
            repro.append(i)
        elif pk == 'error' and ak == 'error':
            # both refuse to answer; only count it when the REASON matches,
            # since 'die: not implemented' and 'timed out' are different facts
            if ('not implemented' in pv) == ('not implemented' in av):
                repro.append(i)
            else:
                unattr.append((i, 'error-reason', av, pv))
        else:
            unattr.append((i, pk + '/' + ak, av, pv))

    # ---- rule 82: the model must also reproduce every case the library PASSES
    fp = []
    verify_skipped = 0
    for i in passed:
        pk, pv = pred_of(i)
        if pk == 'skip':
            verify_skipped += 1
            continue
        if pk != 'occ' or pv != cases[i]['expect']:
            fp.append((i, pk, pv))

    # ---- membership by mechanism, for the reproduced set only
    mech = collections.Counter()
    for i in repro:
        ns = exprs[i]['notes']
        for n in (ns or ['(no rewrite fired)']):
            mech[n] += 1

    shapes = collections.Counter()
    for i, why, av, pv in unattr:
        shapes[(why, freq_of(cases[i]['rrule']))] += 1

    print("failing cases in scored run : %d" % len(failed))
    print("  reproduced                : %d" % len(repro))
    print("  unattributed              : %d" % len(unattr))
    print("  out of scope (BYSETPOS)   : %d" % len(skipped))
    print()
    print("rule 82 replay over the %d passing cases" % len(passed))
    print("  model disagrees on        : %d   <-- must be 0" % len(fp))
    print("  not evaluable (BYSETPOS)  : %d" % verify_skipped)
    print()
    print("mechanisms exercised by the reproduced cases (a case may use several):")
    for n, c in mech.most_common():
        print("  %5d  %s" % (c, n))
    if unattr:
        print()
        print("the unattributed, by (kind, FREQ):")
        for k, c in shapes.most_common():
            print("  %5d  %s" % (c, k))
    if fp:
        print()
        print("VERIFY FAILURES (first 10):")
        for i, k, v in fp[:10]:
            print("  %s %s %s" % (i, cases[i]['rrule'], k))

    json.dump({
        "scored": scored,
        "corpus_version": res.get("corpus_version"),
        "counts": {"failing": len(failed), "reproduced": len(repro),
                   "unattributed": len(unattr), "bysetpos_out_of_scope": len(skipped),
                   "passing": len(passed), "verify_disagreements": len(fp),
                   "verify_not_evaluable": verify_skipped},
        "mechanisms": dict(mech),
        "reproduced_ids": sorted(repro),
        "unattributed": [{"id": i, "kind": w, "actual": a, "predicted": p}
                         for i, w, a, p in unattr],
        "bysetpos_ids": sorted(i for i, _ in skipped),
        "verify_disagreements": [{"id": i, "kind": k, "predicted": v} for i, k, v in fp],
    }, open('findings/data/079-dtical-residual-reproduced.json', 'w'),
        indent=1, sort_keys=True)
    print("\n-> findings/data/079-dtical-residual-reproduced.json")


def freq_of(r):
    for p in r.split(';'):
        if p.upper().startswith('FREQ='):
            return p.upper()[5:]
    return '?'


if __name__ == '__main__':
    main(*sys.argv[1:4])

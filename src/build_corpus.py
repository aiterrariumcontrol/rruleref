"""Build the conformance corpus.

A case earns a place in the corpus only when two independent expanders -- the
spec-derived brute force in naive.py and python-dateutil's interval machinery
-- agree on it. Agreement between implementations that share no code is the
evidence; it is not proof, but it is much stronger than one library's own
regression suite, which by construction cannot disagree with itself.

Cases where they disagree are not silently dropped. They go to
corpus/disputed.json for a human to adjudicate against the spec text.
"""
import sys, json, random
sys.path.insert(0, "/home/agent/terrarium/scratch/pylibs")
sys.path.insert(0, "src")
from datetime import datetime
from differ import compare, gen, DTSTARTS, du_expand, HORIZON_DAYS
from naive import expand

N = 8  # occurrences recorded per case


def fmt(dt):
    return dt.strftime("%Y%m%dT%H%M%S")


def is_synchronized(rule, dtstart):
    """RFC 5545 sec 3.8.5.3: DTSTART SHOULD be synchronized with the rule, and the
    recurrence set is *undefined* when it is not. Operationally, DTSTART is
    synchronized exactly when it is itself the first occurrence the rule
    generates from it."""
    occ = expand(rule, dtstart, limit=1)
    return bool(occ) and occ[0] == dtstart


def dtstart_variants(rule, base):
    """Yield the DTSTARTs to test this rule at.

    The original generator picked DTSTART independently of the rule, which meant
    ~90% of cases landed in the RFC-undefined unsynchronized region. Here we also
    derive a synchronized DTSTART -- the rule's own first occurrence at or after
    `base` -- so the corpus has real coverage of the region the spec actually
    defines.

    Using the naive expander to *choose* DTSTART does not weaken corroboration:
    the case is still adjudicated by naive vs dateutil agreement on the result,
    so a badly chosen DTSTART shows up as a dispute rather than a false pass.
    """
    out = [base]
    occ = expand(rule, base, limit=1)
    if occ and occ[0] != base:
        out.append(occ[0])
    return out


def main(seeds=(7, 11, 13, 17, 23), per=300):
    agreed, disputed, seen = [], [], set()
    for seed in seeds:
        rng = random.Random(seed)
        for _ in range(per):
            rule, base = gen(rng), rng.choice(DTSTARTS)
            for ds in dtstart_variants(rule, base):
                if (rule, ds) in seen:
                    continue
                seen.add((rule, ds))
                synced = is_synchronized(rule, ds)
                diff = compare(rule, ds, N)
                if diff is None:
                    occ = expand(rule, ds, limit=N)[:N]
                    agreed.append({
                        "rrule": rule,
                        "dtstart": fmt(ds),
                        "expect": [fmt(x) for x in occ],
                        "truncated": len(occ) == N,
                        "dtstart_synchronized": synced,
                        "corroborated_by": ["naive-bruteforce", "python-dateutil-2.9.0"],
                    })
                else:
                    mine, theirs = diff
                    disputed.append({
                        "rrule": rule,
                        "dtstart": fmt(ds),
                        "dtstart_synchronized": synced,
                        "naive": mine if isinstance(mine, str) else [fmt(x) for x in mine],
                        "dateutil": theirs if isinstance(theirs, str) else [fmt(x) for x in theirs],
                    })
    agreed.sort(key=lambda c: (c["rrule"], c["dtstart"]))
    disputed.sort(key=lambda c: (c["rrule"], c["dtstart"]))
    meta = {
        "about": "Cross-implementation RFC 5545 RRULE conformance corpus.",
        "horizon_days": HORIZON_DAYS,
        "occurrences_per_case": N,
        "cases": len(agreed),
    }
    json.dump({"meta": meta, "cases": agreed}, open("corpus/corroborated.json", "w"),
              indent=1, sort_keys=True)
    json.dump({"meta": {"about": "Cases where the two expanders disagree. "
                                 "Unadjudicated unless referenced in findings/."},
               "cases": disputed}, open("corpus/disputed.json", "w"),
              indent=1, sort_keys=True)
    print("corroborated=%d disputed=%d (of %d generated)" % (len(agreed), len(disputed), len(seen)))


if __name__ == "__main__":
    main()

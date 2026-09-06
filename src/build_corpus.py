"""Build the conformance corpus.

A case earns a place in the corpus only when two independent expanders -- the
spec-derived brute force in naive.py and python-dateutil's interval machinery
-- agree on it. Agreement between implementations that share no code is the
evidence; it is not proof, but it is much stronger than one library's own
regression suite, which by construction cannot disagree with itself.

Cases where they disagree are not silently dropped. They go to
corpus/disputed.json for a human to adjudicate against the spec text.
"""
import sys, os, json, random
sys.path.insert(0, "/home/agent/terrarium/scratch/pylibs")
sys.path.insert(0, "src")
from datetime import datetime
from differ import compare, gen, DTSTARTS, du_expand, HORIZON_DAYS
from naive import expand
import validity
import coverage
import enumerate_cells

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


def record(rule, ds, cell, agreed, disputed, seen):
    """Adjudicate one (rule, DTSTART) and file it. Returns False if a duplicate."""
    if (rule, ds) in seen:
        return False
    seen.add((rule, ds))
    synced = is_synchronized(rule, ds)
    # RFC 5545 3.3.10 validity is a separate dimension from DTSTART
    # synchronization and from implementation agreement. It is written here,
    # at generation time, so an ordinary rebuild cannot drop it.
    # See tests/test_validity.py.
    rule_valid = validity.is_valid(rule)
    # Which cells of 3.3.10's BYxxx/FREQ table this case exercises. Recorded
    # for every case, random or systematic, so coverage is measurable from the
    # corpus alone. See src/coverage.py and tests/test_coverage.py.
    cells = ["/".join(c) for c in coverage.classify(rule)]
    diff = compare(rule, ds, N)
    if diff is None:
        occ = expand(rule, ds, limit=N)[:N]
        agreed.append({
            "rrule": rule,
            "dtstart": fmt(ds),
            "expect": [fmt(x) for x in occ],
            "truncated": len(occ) == N,
            "dtstart_synchronized": synced,
            "rule_valid": rule_valid,
            "cells": cells,
            "systematic_for": cell,
            "corroborated_by": ["naive-bruteforce", "python-dateutil-2.9.0"],
        })
    else:
        mine, theirs = diff
        disputed.append({
            "rrule": rule,
            "dtstart": fmt(ds),
            "dtstart_synchronized": synced,
            "rule_valid": rule_valid,
            "cells": cells,
            "systematic_for": cell,
            "naive": mine if isinstance(mine, str) else [fmt(x) for x in mine],
            "dateutil": theirs if isinstance(theirs, str) else [fmt(x) for x in theirs],
        })
    return True


def main(seeds=(7, 11, 13, 17, 23), per=300):
    agreed, disputed, seen = [], [], set()
    # Systematic first: one case per permitted cell of the 3.3.10 table, so
    # what the corpus covers does not depend on which seeds were used.
    for cell, rule, ds in enumerate_cells.cases():
        record(rule, ds, "/".join(cell), agreed, disputed, seen)
    for seed in seeds:
        rng = random.Random(seed)
        for _ in range(per):
            rule, base = gen(rng), rng.choice(DTSTARTS)
            for ds in dtstart_variants(rule, base):
                record(rule, ds, None, agreed, disputed, seen)

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
    # Hand adjudications survive regeneration: they live in their own file and
    # are re-attached here by rule+DTSTART.
    adj = {}
    if os.path.exists("corpus/adjudications.json"):
        adj = json.load(open("corpus/adjudications.json"))["cases"]
    hit = 0
    for c in disputed:
        a = adj.get("%s|%s" % (c["rrule"], c["dtstart"]))
        if a:
            c["adjudication"] = a
            hit += 1
    json.dump({"meta": {"about": "Cases where the two expanders disagree. "
                                 "Unadjudicated unless carrying an "
                                 "'adjudication' key (see corpus/"
                                 "adjudications.json and findings/).",
                        "adjudicated": hit, "cases": len(disputed)},
               "cases": disputed}, open("corpus/disputed.json", "w"),
              indent=1, sort_keys=True)
    # Coverage against RFC 5545 3.3.10's own BYxxx/FREQ table. N/A cells are
    # excluded: the spec forbids them, so an empty one is conformance.
    all_cells = ["/".join(c) for c in coverage.cells()]
    hits = {c: 0 for c in all_cells}
    for c in agreed + disputed:
        for k in c["cells"]:
            if k in hits:
                hits[k] += 1
    missing = sorted(k for k, v in hits.items() if v == 0)
    json.dump({"meta": {"about": "Coverage of RFC 5545 3.3.10's BYxxx/FREQ "
                                 "table (N/A cells excluded by construction).",
                        "cells": len(all_cells),
                        "covered": len(all_cells) - len(missing),
                        "uncovered": len(missing)},
               "uncovered": missing,
               "cases_per_cell": hits},
              open("corpus/coverage.json", "w"), indent=1, sort_keys=True)
    print("corroborated=%d disputed=%d (of %d generated)" % (len(agreed), len(disputed), len(seen)))
    print("cells covered=%d/%d uncovered=%s" % (len(all_cells) - len(missing),
                                                len(all_cells), missing or "none"))


if __name__ == "__main__":
    main()

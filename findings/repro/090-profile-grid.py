#!/usr/bin/env python3
"""090 -- the per-(implementation, part) profile grid, derived mechanically.

088 and 089 published per-part over-blame rates and a table of pairwise
Spearman correlations.  Both were assembled by hand from the per-run JSON
files in findings/data/.  Two of 089's five published rho values do not
reproduce under any tie or gating convention (see finding 090).  This script
exists so that no figure in this line of work is ever hand-computed again:
every number 090 publishes is printed by this file from the stored data.

It reads every findings/data/088-necessity-<part>-<impl>.json, takes the
ACCOMPANIED stratum only (rule 97), and reports:

  rate        NOT-NECESSARY / (ATTRIBUTABLE + NOT-NECESSARY), the over-blame
              rate: the share of failures on rules carrying X for which X is
              not necessary to provoke the disagreement.
  gate        cells with fewer than MIN_N attributable-or-not decisions are
              printed but never entered into a correlation or a ranking.
              "too few failures" is a result, not a defect (see dmfs and
              rrule.js, which have no gated cell at all).
  rho         Spearman on the per-part rate over the parts gated in BOTH
              implementations.  Tied rates take AVERAGED ranks; the value
              under arbitrary tie-breaking is printed alongside, because the
              two conventions differ by up to 0.08 here and a published
              figure must say which it used.
  pooled      the field-wide rate, and the same rate with one implementation
              removed.  Rule 98: a pooled rate is a statement about the
              corpus's composition until the per-implementation profiles are
              shown to agree.

Usage:
  090-profile-grid.py                 # table to stdout
  090-profile-grid.py --json PATH     # also write the machine-readable grid
"""
import argparse, collections, glob, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
MIN_N = 10

PART_ORDER = ["bymonth", "byweekno", "byday", "bymonthday",
              "byyearday", "byhour", "byminute", "bysecond"]
LABEL = {"bymonth": "BYMONTH", "byweekno": "BYWEEKNO", "byday": "BYDAY",
         "bymonthday": "BYMONTHDAY", "byyearday": "BYYEARDAY",
         "byhour": "BYHOUR", "byminute": "BYMINUTE", "bysecond": "BYSECOND"}
IMPL_ORDER = ["dateutil", "dmfs", "ical4j411", "ical4j430",
              "icaljs", "rrulejs", "sabre"]


def load():
    grid = collections.defaultdict(dict)
    for path in sorted(glob.glob(os.path.join(DATA, "088-necessity-*.json"))):
        stem = os.path.basename(path)[len("088-necessity-"):-len(".json")]
        part, impl = stem.split("-", 1)
        acc = json.load(open(path))["accompanied"]
        att = acc.get("ATTRIBUTABLE", 0)
        notn = acc.get("NOT-NECESSARY", 0)
        n = att + notn
        grid[impl][part] = {
            "attributable": att, "not_necessary": notn, "n": n,
            "passes": acc.get("passes", 0),
            "no_answer": acc.get("no-answer-original", 0),
            "rate": (notn / n) if n else None,
            "gated": n >= MIN_N,
        }
    return grid


def ranks(rates, keys, average_ties=True):
    order = sorted(keys, key=lambda k: rates[k])
    out, i = {}, 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and rates[order[j + 1]] == rates[order[i]]:
            j += 1
        for offset, k in enumerate(order[i:j + 1]):
            out[k] = ((i + j) / 2 + 1) if average_ties else (i + offset + 1)
        i = j + 1
    return out


def spearman(rates_a, rates_b, keys, average_ties=True):
    ra = ranks(rates_a, keys, average_ties)
    rb = ranks(rates_b, keys, average_ties)
    n = len(keys)
    if n < 3:
        return None
    d2 = sum((ra[k] - rb[k]) ** 2 for k in keys)
    return 1 - 6 * d2 / (n * (n * n - 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    args = ap.parse_args()

    grid = load()
    impls = [i for i in IMPL_ORDER if i in grid] + \
            [i for i in sorted(grid) if i not in IMPL_ORDER]
    parts = [p for p in PART_ORDER if any(p in grid[i] for i in impls)]

    print("over-blame rate (NOT-NECESSARY share of decided failures), "
          "accompanied stratum only")
    print("cells with n < %d are shown in parentheses and are NEVER "
          "correlated or ranked\n" % MIN_N)
    head = "%-11s" % "adapter" + "".join("%13s" % LABEL[p] for p in parts)
    print(head)
    print("-" * len(head))
    for i in impls:
        cells = []
        for p in parts:
            c = grid[i].get(p)
            if c is None or c["n"] == 0:
                cells.append("-")
            elif c["gated"]:
                cells.append("%d%% n=%d" % (round(100 * c["rate"]), c["n"]))
            else:
                cells.append("(%d%% n=%d)" % (round(100 * c["rate"]), c["n"]))
        print("%-11s" % i + "".join("%13s" % c for c in cells))

    print("\npooled, and leave-one-out (rule 98)")
    print("%-11s" % "pooled" + "".join(
        "%13s" % pooled(grid, impls, p) for p in parts))
    for drop in impls:
        keep = [i for i in impls if i != drop]
        row = "".join("%13s" % pooled(grid, keep, p) for p in parts)
        if row.strip() != "".join("%13s" % pooled(grid, impls, p)
                                  for p in parts).strip():
            print("%-11s" % ("  -%s" % drop) + row)

    print("\nprofilable adapters (>= 3 gated parts):")
    prof = [i for i in impls
            if sum(1 for p in grid[i] if grid[i][p]["gated"]) >= 3]
    for i in impls:
        g = sum(1 for p in grid[i] if grid[i][p]["gated"])
        print("  %-11s %d gated part(s)%s" %
              (i, g, "" if i in prof else "   -- NOT profilable"))

    print("\npairwise Spearman on per-part rate, parts gated in both")
    print("%-24s %3s %8s %8s" % ("pair", "n", "rho(avg)", "rho(arb)"))
    pairs = []
    for a in prof:
        for b in prof:
            if a >= b:
                continue
            keys = sorted(p for p in grid[a]
                          if p in grid[b] and grid[a][p]["gated"]
                          and grid[b][p]["gated"])
            ra = {p: grid[a][p]["rate"] for p in keys}
            rb = {p: grid[b][p]["rate"] for p in keys}
            avg = spearman(ra, rb, keys, True)
            arb = spearman(ra, rb, keys, False)
            same = a.startswith("ical4j") and b.startswith("ical4j")
            pairs.append({"a": a, "b": b, "n": len(keys), "parts": keys,
                          "rho_avg_ties": avg, "rho_arbitrary_ties": arb,
                          "same_codebase": same})
            print("%-24s %3d %8s %8s%s" % (
                "%s vs %s" % (a, b), len(keys),
                "n/a" if avg is None else "%+.2f" % avg,
                "n/a" if arb is None else "%+.2f" % arb,
                "   <- same codebase" if same else ""))

    # ---- claim check -------------------------------------------------
    # 089 and 090 both asserted in prose that "every cross-lineage pair is
    # zero or negative" and that "the only positive pair is one codebase at
    # two versions".  Both sentences are false and the table above always
    # showed it: ical4j411 vs icaljs is +0.40 and is cross-lineage.  The
    # figures were produced and correct; the sentence summarising them was
    # not checked against them.  So print the summary statements too, and
    # let the data make them.  See finding 091, rule 101.
    pos        = [q for q in pairs if (q["rho_avg_ties"] or 0) > 0]
    cross      = [q for q in pairs if not q["same_codebase"]]
    cross_pos  = [q for q in cross if (q["rho_avg_ties"] or 0) > 0]
    claims = {
        "positive_pairs":              ["%s vs %s" % (q["a"], q["b"]) for q in pos],
        "cross_lineage_pairs":         ["%s vs %s" % (q["a"], q["b"]) for q in cross],
        "cross_lineage_positive":      ["%s vs %s" % (q["a"], q["b"]) for q in cross_pos],
        "every_cross_lineage_le_zero": not cross_pos,
        "only_positive_pair_is_same_codebase":
            len(pos) == 1 and bool(pos) and pos[0]["same_codebase"],
    }
    print("\nclaim check (rule 101 -- the summary sentence is a claim too)")
    print("  positive pairs:                        %s" %
          (", ".join(claims["positive_pairs"]) or "none"))
    print("  cross-lineage POSITIVE pairs:          %s" %
          (", ".join(claims["cross_lineage_positive"]) or "none"))
    print("  'every cross-lineage pair is <= 0':    %s" %
          claims["every_cross_lineage_le_zero"])
    print("  'only positive pair is same codebase': %s" %
          claims["only_positive_pair_is_same_codebase"])

    # The same third library, correlated against one codebase at two versions.
    # If these disagree in SIGN, the coefficient has no resolution at this n.
    print("\nsign stability across a version bump (n is small -- check it)")
    for other in [i for i in prof if not i.startswith("ical4j")]:
        row = []
        for v in [i for i in prof if i.startswith("ical4j")]:
            for q in pairs:
                if {q["a"], q["b"]} == {v, other} and q["rho_avg_ties"] is not None:
                    row.append((v, q["rho_avg_ties"], q["n"]))
        if len(row) >= 2 and len({r[1] > 0 for r in row}) > 1:
            print("  %-9s SIGN FLIPS: %s" % (other, "  ".join(
                "%s %+.2f (n=%d)" % r for r in row)))
        elif len(row) >= 2:
            print("  %-9s stable:     %s" % (other, "  ".join(
                "%s %+.2f (n=%d)" % r for r in row)))

    if args.json:
        payload = {
            "claims": claims,
            "min_n": MIN_N,
            "stratum": "accompanied",
            "grid": {i: grid[i] for i in impls},
            "profilable": prof,
            "pairs": pairs,
            "pooled": {p: pooled_raw(grid, impls, p) for p in parts},
            "pooled_without": {
                d: {p: pooled_raw(grid, [i for i in impls if i != d], p)
                    for p in parts} for d in impls},
        }
        with open(args.json, "w") as fh:
            json.dump(payload, fh, indent=1, sort_keys=True)
            fh.write("\n")
        print("\n-> %s" % args.json)


def pooled_raw(grid, impls, part):
    att = sum(grid[i][part]["attributable"] for i in impls if part in grid[i])
    notn = sum(grid[i][part]["not_necessary"] for i in impls if part in grid[i])
    n = att + notn
    return {"attributable": att, "not_necessary": notn, "n": n,
            "rate": (notn / n) if n else None}


def pooled(grid, impls, part):
    r = pooled_raw(grid, impls, part)
    if not r["n"]:
        return "-"
    return "%d%% n=%d" % (round(100 * r["rate"]), r["n"])


if __name__ == "__main__":
    main()

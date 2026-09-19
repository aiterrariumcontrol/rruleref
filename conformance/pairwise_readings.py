"""Find cases where two INDEPENDENT lineages agree byte-for-byte on an
occurrence list this corpus records nowhere.

    python3 conformance/pairwise_readings.py \
        --run libical=/tmp/libical.json --run ical4j=/tmp/ical4j.json ...
    python3 conformance/pairwise_readings.py --run ... --show 20

Each --run is NAME=FILE where FILE is a `--json` output of score.py. NAME must
appear in LINEAGE below, because the whole question is about lineage and an
unlabelled run cannot be counted.

Why this exists, and how it differs from finding 058
----------------------------------------------------
058 asked which cases the entire independent field rejects, and found six. That
is the strictest possible filter: a case drops out the moment any one lineage
happens to agree with `expect`. But the evidence that indicts the corpus is not
"everybody rejects it" -- it is "two lineages that share no code landed on the
SAME list, and my corpus does not have that list". That is the standard this
project has used since finding 016 to call something a reading rather than a
bug, and it does not care what a third lineage did.

So this tool drops the intersection and groups by ANSWER instead. For every
case, the failing answers are bucketed by their exact occurrence list; any list
reached by two or more distinct lineages is reported. 058's four cases are a
subset of what this finds by construction.

What counts
-----------
Only bucket `fail` is admitted. That bucket is precisely "not `expect`, not any
recorded `reading_alternatives` entry, and not a proper prefix of either", so
membership already establishes the "records nowhere" half of the claim.
`fail_prefix` and `fail_other_reading_prefix` are excluded because a truncation
of a list the corpus DOES hold is not a rival reading, and `error`/`missing`/
`malformed` carry no answer to agree on.

Empty lists are reported separately and are NOT counted as agreement. Returning
nothing is the universal failure mode -- two libraries that both decline to
implement a rule part produce identical empty output without sharing any
reading of it. score.py excludes empty from its prefix test for the same
reason.

What agreement does NOT establish
---------------------------------
Two things, both learned by running this tool (finding 060).

1. **Agreement inside the corpus bound is not agreement.** Most cases here are
   `COUNT`-bounded at 8. Two implementations doing entirely different things can
   produce the same first eight occurrences and diverge at the ninth. A group
   whose agreed answer runs to the case's bound is reported with `*BOUND` and
   has NOT been tested; re-probe the adapters at a larger limit before treating
   it as a reading.
2. **Agreement is not automatically a reading.** Two lineages can share a
   defect without sharing code, and they can land on the same answer to a
   question RFC 5545 does not decide. A group here is a candidate to
   adjudicate, never a conclusion.

Agreement WITHIN a lineage is not evidence (finding 003): `rrule.js`,
`rust-rrule` and `rrule-go` descend from `python-dateutil`, so they can agree by
copying. A group is reported only when it spans at least two lineages, and the
report names the lineages, not just the adapters.
"""
import json, argparse, collections

# Which lineage each adapter belongs to. Finding 003 for the dateutil ports,
# 024 for the rule that a port casts no independent vote.
LINEAGE = {
    "dateutil": "dateutil", "rrulejs": "dateutil",
    "rust": "dateutil", "go": "dateutil",
    "libical": "libical", "ical4j": "ical4j",
    "dmfs": "dmfs", "sabre": "sabre", "dtical": "dtical",
}


def load(path):
    """id -> (bucket, occurrences-or-None), plus the case record."""
    d = json.load(open(path))
    out, cases = {}, {}
    for f in d["failures"]:
        c = f["case"]
        cases[c["id"]] = c
        occ = (f.get("reply") or {}).get("occurrences")
        out[c["id"]] = (f["bucket"], occ if isinstance(occ, list) else None)
    return out, cases


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", default=[], metavar="NAME=FILE")
    ap.add_argument("--show", type=int, default=10)
    a = ap.parse_args(argv)

    runs, cases = {}, {}
    for spec in a.run:
        name, _, path = spec.partition("=")
        if name not in LINEAGE:
            raise SystemExit("unknown adapter %r; add it to LINEAGE first" % name)
        runs[name], cs = load(path)
        cases.update(cs)
    if len(runs) < 2:
        raise SystemExit("give at least two --run")

    lineages = sorted({LINEAGE[n] for n in runs})
    print("adapters: %s" % ", ".join(sorted(runs)))
    print("lineages: %s" % ", ".join(lineages))

    groups, empties = [], []
    for cid in sorted(cases):
        by_answer = collections.defaultdict(list)
        for name, res in runs.items():
            b, occ = res.get(cid, (None, None))
            if b == "fail" and occ is not None:
                by_answer[tuple(occ)].append(name)
        for answer, names in sorted(by_answer.items()):
            lins = sorted({LINEAGE[n] for n in names})
            if len(lins) < 2:
                continue
            (empties if not answer else groups).append(
                {"id": cid, "rrule": cases[cid]["rrule"],
                 "dtstart": cases[cid]["dtstart"],
                 "expect_bound": cases[cid]["expect_bound"],
                 "adapters": sorted(names), "lineages": lins,
                 "answer": list(answer), "expect": cases[cid]["expect"],
                 # The agreement was never tested past the case's own bound.
                 "bound_limited": (cases[cid]["expect_bound"] == "count"
                                   and len(answer) >= cases[cid]["limit"])})

    print("\ncases with a cross-lineage agreed answer the corpus does not hold: %d"
          % len({g["id"] for g in groups}))
    print("  (groups: %d)" % len(groups))
    print("cross-lineage agreement on the EMPTY list (not counted): %d cases"
          % len({e["id"] for e in empties}))

    pairs = collections.Counter()
    for g in groups:
        for i, x in enumerate(g["lineages"]):
            for y in g["lineages"][i + 1:]:
                pairs[(x, y)] += 1
    if pairs:
        print("\nby lineage pair:")
        for (x, y), n in sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0])):
            print("  %-10s %-10s %4d" % (x, y, n))

    nb = sum(1 for g in groups if g["bound_limited"])
    if nb:
        print("\n  *BOUND: %d group(s) agree only as far as the case's own COUNT."
              "\n  That is not agreement until re-probed at a larger limit (060)." % nb)

    for g in groups[:a.show]:
        print("\n  %s  %s%s" % (g["id"], " + ".join(g["lineages"]),
                                 "  *BOUND" if g["bound_limited"] else ""))
        print("    RRULE:%s  DTSTART:%s  (%s)"
              % (g["rrule"], g["dtstart"], g["expect_bound"]))
        print("    adapters: %s" % ", ".join(g["adapters"]))
        print("    expect:   %s" % g["expect"])
        print("    agreed:   %s" % g["answer"])
    if len(groups) > a.show:
        print("\n  ... %d more" % (len(groups) - a.show))
    return groups


if __name__ == "__main__":
    main()

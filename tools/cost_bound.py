"""What would it cost to raise the corpus occurrence bound?

Findings 058, 060 and 061 each probed past the corpus's eight-occurrence bound
without moving it, and 061 showed that `reading_dependent` is a property of the
window rather than of the rule. The honest consequence is to ask what raising
N actually costs. This script measures that rather than guessing it.

It does NOT rebuild the corpus. It runs the real builder's own `record()` --
rule 57: a scratch reimplementation of a corpus rule is not the corpus rule --
over a deterministic sample of the generator's own (rule, DTSTART) stream, once
per candidate N, and reports wall time per case broken down by whether the case
corroborates, disputes, or carries a rival reading.

Extrapolating a sample to the whole generator assumes the sample is
representative of it. The sample is taken by striding the generator's stream in
its natural order, which interleaves the systematic cases (cells, branches,
pairs) with the five random seeds, so it is not a slice of one kind of case.
The extrapolation is reported as a separate, clearly-labelled number.
"""
import sys, os, time, json, random, argparse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import build_corpus as B
import enumerate_cells, enumerate_branches, pairs
from differ import gen, DTSTARTS


def stream():
    """The generator's own (rule, dtstart) stream, in the builder's order."""
    for cell, rule, ds in enumerate_cells.cases():
        yield rule, ds
    for feature, rule, ds in enumerate_branches.cases():
        yield rule, ds
    for pair, rule, ds in pairs.cases():
        yield rule, ds
    for seed in (7, 11, 13, 17, 23):
        rng = random.Random(seed)
        for _ in range(300):
            rule, base = gen(rng), rng.choice(DTSTARTS)
            for d in B.dtstart_variants(rule, base):
                yield rule, d


def sample(stride):
    """Stride the stream's *distinct* cases, so the extrapolation base is the
    same 'generated' count the builder prints. Duplicates cost nothing: the
    builder's `record` returns immediately on them."""
    cases, total, seen = [], 0, set()
    for rule, ds in stream():
        if (rule, ds) in seen:
            continue
        seen.add((rule, ds))
        if total % stride == 0:
            cases.append((rule, ds))
        total += 1
    return cases, total


def run(cases, n):
    """Time the real record() over `cases` with the builder's N set to `n`."""
    old = B.N
    B.N = n
    agreed, disputed, seen = [], [], set()
    rows = []
    try:
        for rule, ds in cases:
            t = time.time()
            na, nd = len(agreed), len(disputed)
            B.record(rule, ds, None, agreed, disputed, seen)
            dt = time.time() - t
            kind = "dup"
            reading = False
            if len(agreed) > na:
                kind = "corroborated"
                reading = bool(agreed[-1].get("reading_alternatives"))
            elif len(disputed) > nd:
                kind = "disputed"
            rows.append({"rrule": rule, "dtstart": B.fmt(ds), "secs": dt,
                         "kind": kind, "reading": reading})
    finally:
        B.N = old
    return rows


def summarise(n, rows, total, sampled):
    tot = sum(r["secs"] for r in rows)
    by = {}
    for r in rows:
        k = r["kind"] + ("+reading" if r["reading"] else "")
        b = by.setdefault(k, [0, 0.0])
        b[0] += 1
        b[1] += r["secs"]
    slow = sorted(rows, key=lambda r: -r["secs"])[:5]
    return {
        "N": n,
        "sampled_cases": sampled,
        "generator_cases": total,
        "sample_secs": round(tot, 2),
        "secs_per_case": round(tot / max(len(rows), 1), 4),
        "extrapolated_full_build_secs": round(tot / max(len(rows), 1) * total, 1),
        "by_kind": {k: {"cases": v[0], "secs": round(v[1], 2),
                        "secs_per_case": round(v[1] / v[0], 4)}
                    for k, v in sorted(by.items())},
        "slowest": [{"rrule": r["rrule"], "dtstart": r["dtstart"],
                     "secs": round(r["secs"], 3)} for r in slow],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stride", type=int, default=40,
                    help="take every Nth case of the generator's stream")
    ap.add_argument("--limits", default="8,16,25")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    cases, total = sample(a.stride)
    print("sample: %d of %d generated cases (stride %d)" % (len(cases), total, a.stride),
          file=sys.stderr)
    out = []
    for n in [int(x) for x in a.limits.split(",")]:
        rows = run(cases, n)
        s = summarise(n, rows, total, len(cases))
        out.append(s)
        print("N=%-3d sample=%7.1fs  per_case=%.4fs  extrapolated_full=%.0fs" % (
            n, s["sample_secs"], s["secs_per_case"],
            s["extrapolated_full_build_secs"]), file=sys.stderr)
    doc = {"meta": {"about": "Cost of raising the corpus occurrence bound.",
                    "stride": a.stride, "generator_cases": total,
                    "sampled_cases": len(cases),
                    "caveat": "Extrapolation assumes the strided sample is "
                              "representative of the whole generator stream."},
           "runs": out}
    if a.out:
        json.dump(doc, open(a.out, "w"), indent=1, sort_keys=True)
    else:
        json.dump(doc, sys.stdout, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()

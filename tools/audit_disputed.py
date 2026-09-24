"""Run the disputed cases against implementations, or classify what came back.

`corpus/disputed.json` is the part of the corpus the two adjudicators could not
agree on, and until finding 081 it was the only part that had never been shown
to an implementation: `conformance/build_cases.py` selects *corroborated* cases,
so a disputed case is in no adapter run anywhere on RESULTS.md.

    python3 tools/audit_disputed.py --emit > disputed.ndjson
    <adapter> < disputed.ndjson > out.<name>.ndjson       # PROTOCOL.md, unchanged
    python3 tools/audit_disputed.py --classify out.*.ndjson

`--classify` prints one row per case and one summary line per adapter. Each
answer is classified against the two adjudicators' recorded lists:

    N    equals `naive`      D    equals `dateutil`
    X    a third answer      ERR  the adapter refused the rule

There is no partial credit here either, and no bucket for "close": an answer is
one of the two recorded lists or it is a third thing.

Two controls run on every `--classify`, and both must be clean before any row
below may be cited:

  * `naive.expand` re-derives the recorded `naive` list for all 28 cases;
  * if a `dateutil` adapter output is among the files, it must equal the
    recorded `dateutil` list for all 28.

The second is what makes the rest meaningful. `disputed.json` records a
disagreement observed when the case was admitted; if the adapter no longer
reproduces it, the disagreement is stale and the verdict is about a library
that no longer exists.
"""
import argparse, datetime, hashlib, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
import naive  # noqa: E402

LIMIT = 25
FMT = "%Y%m%dT%H%M%S"


def load_cases():
    """The 28 disputed cases, keyed by the same id build_cases.py would give."""
    cases, order = {}, []
    path = os.path.join(REPO, "corpus", "disputed.json")
    with open(path) as f:
        disputed = json.load(f)["cases"]
    for c in disputed:
        cid = hashlib.sha256(
            ("%s\n%s" % (c["rrule"], c["dtstart"])).encode()).hexdigest()[:12]
        cases[cid] = c
        order.append(cid)
    return cases, order


def expand_naive(rrule, dtstart, limit=LIMIT):
    ds = datetime.datetime.strptime(dtstart, FMT)
    return [x.strftime(FMT) for x in naive.expand(rrule, ds, limit=limit)][:limit]


def emit(out):
    cases, order = load_cases()
    for cid in order:
        c = cases[cid]
        out.write(json.dumps({"id": cid, "rrule": c["rrule"],
                              "dtstart": c["dtstart"], "limit": LIMIT},
                             sort_keys=True) + "\n")


def read_out(path):
    d = {}
    with open(path) as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        if line:
            o = json.loads(line)
            d[o["id"]] = o
    return d


def classify(answer, case):
    """One of N, D, X, ERR. None is ERR, never a match for another None."""
    if answer is None:
        return "ERR"
    if answer == case["naive"]:
        return "N"
    if answer == case["dateutil"]:
        return "D"
    return "X"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--emit", action="store_true",
                    help="write the 28 disputed cases as PROTOCOL.md input")
    ap.add_argument("--classify", nargs="*", metavar="OUT",
                    help="adapter output files, named out.<adapter>.ndjson")
    ap.add_argument("--json", metavar="PATH", help="write the table as JSON")
    a = ap.parse_args(argv)

    if a.emit:
        emit(sys.stdout)
        return 0
    if a.classify is None:
        ap.error("one of --emit or --classify is required")

    cases, order = load_cases()

    # Control 1: the expander re-derives its own recorded answers.
    drift = [cid for cid in order
             if expand_naive(cases[cid]["rrule"], cases[cid]["dtstart"])
             != cases[cid]["naive"]]
    print("control: naive.expand vs recorded naive -- %d/%d reproduced"
          % (len(order) - len(drift), len(order)))
    if drift:
        print("  DRIFTED: %s" % ", ".join(drift))

    outs = {}
    for p in a.classify:
        name = os.path.basename(p)
        for pre, suf in (("out.", ".ndjson"),):
            if name.startswith(pre):
                name = name[len(pre):]
            if name.endswith(suf):
                name = name[:-len(suf)]
        outs[name] = read_out(p)

    # Control 2: a dateutil adapter must still reproduce the recorded dispute.
    for name in outs:
        if name == "dateutil":
            stale = [cid for cid in order
                     if outs[name].get(cid, {}).get("occurrences")
                     != cases[cid]["dateutil"]]
            print("control: dateutil adapter vs recorded dateutil -- "
                  "%d/%d reproduced" % (len(order) - len(stale), len(order)))
            if stale:
                print("  STALE: %s" % ", ".join(stale))

    names = sorted(outs)
    table = []
    for cid in order:
        c = cases[cid]
        row = {"id": cid, "rrule": c["rrule"], "dtstart": c["dtstart"],
               "synchronized": bool(c["dtstart_synchronized"]),
               "verdict": c.get("adjudication", {}).get("verdict"),
               "finding": c.get("adjudication", {}).get("finding"),
               "answers": {n: classify(outs[n].get(cid, {}).get("occurrences"), c)
                           for n in names}}
        table.append(row)

    w = max([len(n) for n in names] + [4])
    print()
    print("%-12s %-9s %-4s %s" % ("case", "verdict", "sync",
                                  " ".join(n.ljust(w) for n in names)))
    for r in table:
        print("%-12s %-9s %-4s %s"
              % (r["id"], r["verdict"] or "-", "S" if r["synchronized"] else "u",
                 " ".join(r["answers"][n].ljust(w) for n in names)))
    print()
    for n in names:
        cnt = {k: 0 for k in "NDX"}
        cnt["ERR"] = 0
        for r in table:
            cnt[r["answers"][n]] += 1
        print("%-*s  naive=%-3d dateutil=%-3d third=%-3d error=%d"
              % (w, n, cnt["N"], cnt["D"], cnt["X"], cnt["ERR"]))

    if a.json:
        with open(a.json, "w") as f:
            json.dump({"limit": LIMIT, "adapters": names, "cases": table},
                      f, indent=1, sort_keys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

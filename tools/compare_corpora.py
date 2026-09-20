"""Diff two corpus builds produced by `src/build_corpus.py`.

Findings 062 and 064 each moved one corpus parameter and compared the result
against the committed build by hand. The two parameters interact -- a higher
occurrence bound converts `count`-bounded cases into `horizon`-bounded ones
(062) and a longer horizon converts them back (064) -- so they cannot be
chosen one at a time, and comparing four builds by hand is how a count gets
published wrong (standing rules 53 and 54).

This reports, for any two builds:

  * corroborated/disputed counts *and membership*, never just the counts;
  * the `expect_bound` distribution and where each case moved;
  * whether every shared case's `expect` in B extends A's as a prefix,
    which is the check that says "this build adds evidence, it does not
    revise any";
  * which cases changed the set of rival readings they carry.

Usage:  python3 tools/compare_corpora.py DIR_A DIR_B [--label-a X --label-b Y]
"""
import json, os, sys, argparse, collections


def load(d):
    out = {}
    for name in ("corroborated", "disputed"):
        p = os.path.join(d, name + ".json")
        blob = json.load(open(p))
        out[name] = {(c["rrule"], c["dtstart"]): c for c in blob["cases"]}
        out.setdefault("meta", {})[name] = blob.get("meta", {})
    return out


def is_prefix(short, long_):
    return len(short) <= len(long_) and list(short) == list(long_[:len(short)])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dir_a")
    ap.add_argument("dir_b")
    ap.add_argument("--label-a", default=None)
    ap.add_argument("--label-b", default=None)
    ap.add_argument("--json", help="write the machine-readable diff here")
    a_ns = ap.parse_args(argv)
    la = a_ns.label_a or a_ns.dir_a
    lb = a_ns.label_b or a_ns.dir_b

    A, B = load(a_ns.dir_a), load(a_ns.dir_b)
    rep = {"a": la, "b": lb, "meta_a": A["meta"], "meta_b": B["meta"]}

    print("%-28s %12s %12s" % ("", la, lb))
    for name in ("corroborated", "disputed"):
        print("%-28s %12d %12d" % (name, len(A[name]), len(B[name])))
    rep["counts"] = {n: [len(A[n]), len(B[n])] for n in ("corroborated", "disputed")}

    # Membership, not counts. Two builds can hold the same number of
    # corroborated cases and not the same cases (standing rule 54).
    lost = sorted(set(A["corroborated"]) - set(B["corroborated"]))
    gained = sorted(set(B["corroborated"]) - set(A["corroborated"]))
    rep["lost_corroboration"] = lost
    rep["gained_corroboration"] = gained
    print("\ncorroboration lost   %d" % len(lost))
    for k in lost[:20]:
        print("    %s  DTSTART=%s" % k)
    print("corroboration gained %d" % len(gained))
    for k in gained[:20]:
        print("    %s  DTSTART=%s" % k)

    # expect_bound, with the moves named rather than only the totals.
    ba = collections.Counter(c["expect_bound"] for c in A["corroborated"].values())
    bb = collections.Counter(c["expect_bound"] for c in B["corroborated"].values())
    print("\nexpect_bound")
    for k in sorted(set(ba) | set(bb)):
        print("    %-10s %6d -> %6d" % (k, ba[k], bb[k]))
    moves = collections.Counter()
    shared = set(A["corroborated"]) & set(B["corroborated"])
    for k in shared:
        x, y = A["corroborated"][k]["expect_bound"], B["corroborated"][k]["expect_bound"]
        if x != y:
            moves[(x, y)] += 1
    print("  moves among the %d shared cases:" % len(shared))
    for (x, y), n in moves.most_common():
        print("    %-10s -> %-10s %6d" % (x, y, n))
    rep["bound_totals"] = {"a": dict(ba), "b": dict(bb)}
    rep["bound_moves"] = {"%s->%s" % k: v for k, v in moves.items()}

    # Does B extend A, or revise it?
    revised = [k for k in shared
               if not is_prefix(A["corroborated"][k]["expect"],
                                B["corroborated"][k]["expect"])]
    print("\nexpect is a prefix-extension in %d/%d shared cases (%d exceptions)"
          % (len(shared) - len(revised), len(shared), len(revised)))
    for k in revised[:20]:
        print("    %s  DTSTART=%s" % k)
    rep["revised_expect"] = revised

    # Rival readings: which cases carry a different set than before.
    def rk(c):
        return sorted((c.get("reading_alternatives") or {}).keys())
    changed = [k for k in shared if rk(A["corroborated"][k]) != rk(B["corroborated"][k])]
    print("\nreading set changed in %d shared cases" % len(changed))
    for k in changed[:20]:
        print("    %s  DTSTART=%s\n        %s -> %s"
              % (k[0], k[1], rk(A["corroborated"][k]), rk(B["corroborated"][k])))
    rep["changed_readings"] = changed
    rdep = (sum(1 for c in A["corroborated"].values() if c["reading_dependent"]),
            sum(1 for c in B["corroborated"].values() if c["reading_dependent"]))
    print("reading_dependent %d -> %d" % rdep)
    rep["reading_dependent"] = list(rdep)

    if a_ns.json:
        json.dump(rep, open(a_ns.json, "w"), indent=1, default=list)
        print("\nwrote %s" % a_ns.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())

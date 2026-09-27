#!/usr/bin/env python3
"""Finding 113 -- libical master's 19 -> 6 improvement is ONE upstream commit.

Finding 112 partitioned libical master `4edd39a3`'s six-case `fail` bucket into
two BYWEEKNO defects, A and B, and explicitly did NOT claim the older master
build `48d52b4b` (19 fail) or the released `3.0.20` (107 fail). This closes the
`48d52b4b` half, and it does it WITHOUT WRITING A PATCH: the subject is a git
history, so the removal step is already committed. Rule 117 attributes by
removal; here the thing removed is an upstream commit, not a patch of mine.

WHAT IS MEASURED

Fifteen commits separate `48d52b4b` from `4edd39a3`. Exactly two touch
`src/libical/icalrecur.c`:

  * `ce5332a` "icalrecur.c - fix right shift overview warning (#1378)", a bounds
    guard in ``daysmask_set_range``;
  * `4edd39a` "BYSETPOS issue fix (#1387)", six hunks confined to
    ``icalrecur_iterator_next`` and ``icalrecur_iterator_prev``.

Building `cefc9ca` -- the parent of `4edd39a`, and downstream of `ce5332a` --
separates them. The result:

  48d52b4b   pass 1601  fail 19   fail_other_reading 72  error 35
  cefc9ca    pass 1601  fail 19   fail_other_reading 72  error 35   <- identical
  4edd39a3   pass 1614  fail  6   fail_other_reading 72  error 35

`cefc9ca` and `48d52b4b` agree ID FOR ID, not merely in count, so the whole
13-case improvement belongs to the single commit `4edd39a`, with ZERO
regressions. The warning fix moved nothing.

WHY THE 6 THAT REMAIN ARE 112'S A AND B, AND NOT A NEW CLAIM

fail(4edd39a3) is a STRICT SUBSET of fail(48d52b4b), and both of 112's defect
sites are byte-identical at the same line numbers in both commits
(``weeks_in_year()`` whole-body diff empty; the ``last_day = (7 *
weeks_in_year(year)) - doy_offset - 1`` site unchanged). So `48d52b4b`'s bucket
partitions as 13 + 6 and the 6 carry 112's labels unchanged. This finding does
not re-derive A and B; it inherits them.

THE SIGNATURE, WHICH IS CORROBORATION AND NOT THE ARGUMENT

All 13 cases `4edd39a` fixes are `FREQ=WEEKLY` with `BYSETPOS`, matching the
commit subject. None of the 6 that remain use `BYSETPOS` at `FREQ=WEEKLY`. The
attribution above rests on the build, not on this; the signature is reported
because a 13/13 match against the commit message is worth stating.

RUNNING IT

  python3 findings/repro/113-one-commit-thirteen-cases.py           # ~40s, 3 builds
  python3 findings/repro/113-one-commit-thirteen-cases.py --check   # the guard

Needs three install prefixes, none of which is in the tree, and a libical git
checkout for the textual half. Rule 102: this script only READS prefixes; it
builds nothing and installs nothing. It is therefore safe beside the canonical
`libical-install-4edd` that every published libical row is measured through.
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARTIFACT = os.path.join(ROOT, "findings", "data", "113-one-commit-thirteen-cases.json")
ADAPTER = os.path.join(ROOT, "conformance", "adapters", "c", "libical_adapter")
SRC = os.environ.get("LIBICAL_SRC", "/home/agent/terrarium/scratch/libical")
SCRATCH = os.environ.get("LIBICAL_SCRATCH", "/home/agent/terrarium/scratch")

CASES_ID = "7bd9731d3a48c0155ba35f943d43756ff2ec8ae69cced3464d45940e62e53f5b"

# commit -> install prefix. Each was configured identically (Release, no
# bindings, ICU found), so the only difference between them is the source.
BUILDS = [
    ("48d52b4b", os.path.join(SCRATCH, "libical-install")),
    ("cefc9ca",  os.path.join(SCRATCH, "libical-install-cefc9ca")),
    ("4edd39a3", os.path.join(SCRATCH, "libical-install-4edd")),
]

# Inherited from finding 112 unchanged. Verified here to be textually present
# in 48d52b4b as well, which is what licenses reusing the labels.
RESIDUE = {
    "112 A-weeks-in-year-ignores-wkst": [
        "1b491afa4ef0", "47957affeae1", "6a2a3349a31d", "cd5d1f7e7232",
    ],
    "112 B-week-year-truncated-by-doy-offset-plus-one": [
        "52cb89bd1169", "a11bc9303af3",
    ],
}


def score(prefix):
    """Run the committed adapter against one prefix; return (counts, fail ids)."""
    out = os.path.join("/tmp", "113-%s.json" % os.path.basename(prefix))
    env = dict(os.environ, TZ="UTC",
               LD_LIBRARY_PATH=os.path.join(prefix, "lib"))
    # score.py exits non-zero whenever anything failed, which is normal here;
    # the artifact is the result, not the return code.
    subprocess.run([sys.executable, "conformance/score.py", "--json", out,
                    "--", ADAPTER],
                   cwd=ROOT, env=env, capture_output=True, text=True)
    if not os.path.exists(out):
        sys.exit("score.py produced no artifact for %s" % prefix)
    d = json.load(open(out))
    if d["corpus_version"]["cases_id"] != CASES_ID:
        sys.exit("corpus moved: %s" % d["corpus_version"]["cases_id"])
    return d["counts"], {f["case"]["id"] for f in d["failures"]
                         if f["bucket"] == "fail"}


def git(*a):
    return subprocess.run(("git",) + a, cwd=SRC, capture_output=True,
                          text=True).stdout


def rules_for(ids):
    out = {}
    with open(os.path.join(ROOT, "conformance", "cases.ndjson")) as fh:
        for line in fh:
            c = json.loads(line)
            if c["id"] in ids:
                out[c["id"]] = c["rrule"]
    return out


def compute():
    res = {"cases_id": CASES_ID, "subject": "libical master, 48d52b4b..4edd39a3",
           "counts": {}, "fail": {}}
    for commit, prefix in BUILDS:
        counts, fails = score(prefix)
        res["counts"][commit] = counts
        res["fail"][commit] = sorted(fails)

    old = set(res["fail"]["48d52b4b"])
    mid = set(res["fail"]["cefc9ca"])
    new = set(res["fail"]["4edd39a3"])
    res["parent_identical_to_base"] = (mid == old)
    res["new_is_strict_subset"] = (new < old)
    res["regressions"] = sorted(new - mid)
    res["fixed_by_4edd39a"] = sorted(mid - new)
    res["rules_fixed"] = rules_for(mid - new)
    res["signature_all_weekly_bysetpos"] = all(
        "FREQ=WEEKLY" in r and "BYSETPOS" in r
        for r in res["rules_fixed"].values())
    res["residue_partition"] = {k: sorted(v) for k, v in RESIDUE.items()}

    # commits in the range, and which of them touch the recurrence engine
    rng = "48d52b4b..4edd39a"
    res["commits_in_range"] = len([l for l in git("rev-list", rng).split() if l])
    res["commits_touching_icalrecur"] = [
        l.split()[0] for l in
        git("log", "--oneline", rng, "--", "src/libical/icalrecur.c").splitlines()]

    # the textual half: 112's two defect sites, unchanged across the range
    a = git("show", "48d52b4b:src/libical/icalrecur.c")
    b = git("show", "4edd39a:src/libical/icalrecur.c")

    def body(src, marker, end="\n}\n"):
        i = src.find(marker)
        return None if i < 0 else src[i:src.find(end, i) + len(end)]

    wa, wb = body(a, "static int weeks_in_year"), body(b, "static int weeks_in_year")
    site = "last_day = (7 * weeks_in_year(year)) - doy_offset - 1;"
    res["defect_sites_unchanged"] = {
        "A-weeks-in-year-body": bool(wa) and wa == wb,
        "B-last-day-site": a.count(site) == 1 and b.count(site) == 1,
    }
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify the stored artifact against a fresh run")
    args = ap.parse_args()

    missing = [p for _, p in BUILDS if not os.path.isdir(os.path.join(p, "lib"))]
    if missing or not os.path.isdir(os.path.join(SRC, ".git")):
        print("skip  need all three libical prefixes and a source checkout")
        for m in missing:
            print("        absent: %s" % m)
        return 0

    fresh = compute()
    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        ok = ok and bool(cond)
        print("%-4s %s%s" % ("ok" if cond else "FAIL", label,
                             ("   %s" % detail) if detail else ""))

    for commit, _ in BUILDS:
        c = fresh["counts"][commit]
        print("     %-9s pass %d  fail %d  other %d  error %d"
              % (commit, c["pass"], c["fail"], c["fail_other_reading"],
                 c["error"]))

    check("cefc9ca's fail bucket is identical to 48d52b4b's, id for id",
          fresh["parent_identical_to_base"])
    check("4edd39a3's bucket is a strict subset of its parent's",
          fresh["new_is_strict_subset"])
    check("one commit, 4edd39a, fixed 13 cases",
          len(fresh["fixed_by_4edd39a"]) == 13,
          "%d" % len(fresh["fixed_by_4edd39a"]))
    check("and produced no regression", not fresh["regressions"])
    check("exactly two commits in the range touch icalrecur.c",
          len(fresh["commits_touching_icalrecur"]) == 2,
          ", ".join(fresh["commits_touching_icalrecur"]))
    check("all 13 are FREQ=WEEKLY with BYSETPOS",
          fresh["signature_all_weekly_bysetpos"])
    check("112's two defect sites are unchanged across the range",
          all(fresh["defect_sites_unchanged"].values()),
          json.dumps(fresh["defect_sites_unchanged"]))
    residue = sorted(i for v in RESIDUE.values() for i in v)
    check("the 6 that remain are exactly 112's A+B",
          residue == fresh["fail"]["4edd39a3"])
    check("13 + 6 partitions 48d52b4b's bucket of 19",
          sorted(fresh["fixed_by_4edd39a"] + residue) == fresh["fail"]["48d52b4b"])

    if args.check:
        if not os.path.exists(ARTIFACT):
            print("FAIL no stored artifact at %s" % ARTIFACT)
            return 1
        stored = json.load(open(ARTIFACT))
        same = stored == fresh
        check("stored artifact matches a fresh computation (rule 115)", same)
        if not same:
            for k in sorted(set(stored) | set(fresh)):
                if stored.get(k) != fresh.get(k):
                    print("       differs: %s" % k)
    else:
        with open(ARTIFACT, "w") as fh:
            json.dump(fresh, fh, indent=1, sort_keys=True)
            fh.write("\n")
        print("     wrote %s" % os.path.relpath(ARTIFACT, ROOT))

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

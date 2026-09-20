#!/usr/bin/env python3
"""Give the corpus and the scorer content identifiers, so a published count can
be checked for staleness mechanically instead of remembered.

WHY
---
Every number this project publishes -- a conformance/RESULTS.md row, a count in
a finding, a claim in the README -- is a measurement of one *adapter* against
one *corpus* through one *scorer*. The adapter is always named. The other two
never were. So a row measured before the corpus bound rose from 8 to 25
occurrences (finding 066), or before 285 cases changed `expect_bound` (067,
applied at wake 103), looks exactly like a row measured after it, and the only
thing standing between a reader and a stale number was my memory of what had
changed since.

This module replaces that memory with two hashes:

    corpus_id   sha256 over every committed corpus data file and the scored
                case list, in a fixed order -- the corpus as a whole.
    cases_id    sha256 over conformance/cases.ndjson alone -- the bytes a
                conformance run actually reads. This is the finer identifier
                and the one a RESULTS.md row turns on: the corpus can change
                (067 relabelled 285 cases) without the scored subset moving at
                all, and two rows with the same cases_id are comparable even
                when their corpus_id differs.
    scorer_id   sha256 over conformance/score.py -- the *procedure*.

A published measurement that names both is checkable: recompute, compare, and
if either differs the number is from a different experiment and has to be
re-run before it may be cited. That is finding-053's rule, made mechanical.

WHAT THE IDS DO NOT COVER
-------------------------
The adapters, the libraries they bind, and the host interpreters are not
hashed. Two runs with the same pair of ids can still differ because the
implementation under test moved -- that is the thing being measured, and it is
named in the row. `src/` is not hashed either: the expander only reaches a
measurement through the corpus it built, which is hashed.

USAGE
-----
    python3 tools/corpus_id.py             # print the ids and the parameters
    python3 tools/corpus_id.py --write     # record them in corpus/VERSION.json
    python3 tools/corpus_id.py --check     # exit 1 if the record is stale
"""
import argparse, hashlib, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = os.path.join(REPO, "corpus", "VERSION.json")

# Fixed order: the id must not depend on how a directory happens to list.
# corpus/VERSION.json is deliberately absent -- a record cannot hash itself.
CORPUS_FILES = [
    "conformance/cases.ndjson",
    "corpus/adjudications.json",
    "corpus/corroborated.json",
    "corpus/coverage.json",
    "corpus/date-value-type.json",
    "corpus/disputed.json",
    "corpus/grammar-coverage.json",
    "corpus/pair-coverage.json",
    "corpus/rfc5545-examples.json",
]
SCORER_FILES = ["conformance/score.py"]
CASES_FILES = ["conformance/cases.ndjson"]  # a subset of CORPUS_FILES

# Written by a human, recomputed by nobody.
HUMAN_FIELDS = ["version", "version_means"]


def unlisted_corpus_files():
    """Data files in corpus/ that no identifier covers.

    The file list above is written by hand, which means a file added to
    corpus/ later is hashed by nobody and changes no id -- the same shape of
    failure as finding 068's third copy, where a fact stated once in a list
    was relied on for weeks. So the list is checked against the directory
    rather than trusted. VERSION.json is excluded: it cannot hash itself.
    """
    listed = set(CORPUS_FILES + SCORER_FILES)
    found = []
    for name in sorted(os.listdir(os.path.join(REPO, "corpus"))):
        if not name.endswith(".json") or name == "VERSION.json":
            continue
        rel = "corpus/" + name
        if rel not in listed:
            found.append(rel)
    return found


def _sha256(path):
    h = hashlib.sha256()
    with open(os.path.join(REPO, path), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _combine(paths, digests):
    """Hash the (name, digest) pairs, not the concatenated bytes.

    Hashing concatenated content would give the same id if a byte moved from
    the end of one file to the start of the next. Binding each digest to its
    path also makes a renamed or dropped file change the id, which is the
    point: the id names a file *set*.
    """
    h = hashlib.sha256()
    for p in paths:
        h.update(("%s %s\n" % (p, digests[p])).encode("ascii"))
    return h.hexdigest()


def compute():
    digests = {p: _sha256(p) for p in CORPUS_FILES + SCORER_FILES}
    def _load(name):
        with open(os.path.join(REPO, "corpus", name)) as fh:
            return json.load(fh)
    corroborated = _load("corroborated.json")
    disputed = _load("disputed.json")
    meta = corroborated["meta"]
    bounds = {}
    for c in corroborated["cases"]:
        bounds[c["expect_bound"]] = bounds.get(c["expect_bound"], 0) + 1
    with open(os.path.join(REPO, "conformance", "cases.ndjson")) as fh:
        scored = sum(1 for line in fh if line.strip())
    return {
        "corpus_id": _combine(CORPUS_FILES, digests),
        "cases_id": _combine(CASES_FILES, digests),
        "scorer_id": _combine(SCORER_FILES, digests),
        "occurrences_per_case": meta["occurrences_per_case"],
        "horizon_days": meta["horizon_days"],
        "corroborated_cases": len(corroborated["cases"]),
        "disputed_cases": len(disputed["cases"]),
        "scored_cases": scored,
        "expect_bound": {k: bounds[k] for k in sorted(bounds)},
        "files": {p: digests[p] for p in CORPUS_FILES + SCORER_FILES},
    }


def read_recorded():
    if not os.path.exists(VERSION_FILE):
        return None
    with open(VERSION_FILE) as fh:
        return json.load(fh)


def short(ident):
    """Twelve hex digits. Long enough that a collision is not a real risk here,
    short enough to sit in a table header without pushing the row off a line."""
    return ident[:12]


def _write(computed):
    recorded = read_recorded() or {}
    out = dict(computed)
    # The human-set fields survive a --write; everything else is recomputed.
    # A tool that silently deleted the prose a human wrote would only have to
    # do it once to stop anyone writing prose there.
    for k in HUMAN_FIELDS:
        if k in recorded:
            out[k] = recorded[k]
    out.setdefault("version", "0")
    out["about"] = ("Content identifiers for the corpus and the scorer. "
                    "Recompute with tools/corpus_id.py; a measurement that "
                    "names a different pair is from a different experiment.")
    ordered = {k: out[k] for k in ["about", "version", "version_means",
                                   "corpus_id", "cases_id", "scorer_id"]
               if k in out}
    ordered.update({k: v for k, v in out.items() if k not in ordered})
    with open(VERSION_FILE, "w") as fh:
        json.dump(ordered, fh, indent=1, sort_keys=False)
        fh.write("\n")
    return ordered


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true",
                    help="record the computed ids in corpus/VERSION.json")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if corpus/VERSION.json is stale")
    a = ap.parse_args(argv)
    unlisted = unlisted_corpus_files()
    if unlisted:
        print("WARNING: no identifier covers %s -- add it to CORPUS_FILES"
              % ", ".join(unlisted), file=sys.stderr)
    computed = compute()
    if a.write:
        _write(computed)
        print("wrote %s" % os.path.relpath(VERSION_FILE, REPO))
    recorded = read_recorded()
    print("corpus_id  %s" % computed["corpus_id"])
    print("cases_id   %s" % computed["cases_id"])
    print("scorer_id  %s" % computed["scorer_id"])
    print("N=%d  horizon_days=%d  corroborated=%d  disputed=%d  scored=%d"
          % (computed["occurrences_per_case"], computed["horizon_days"],
             computed["corroborated_cases"], computed["disputed_cases"],
             computed["scored_cases"]))
    print("expect_bound %s" % computed["expect_bound"])
    if a.check:
        if recorded is None:
            print("STALE: no corpus/VERSION.json; run --write", file=sys.stderr)
            return 1
        if unlisted:
            return 1
        drifted = [k for k in ("corpus_id", "cases_id", "scorer_id")
                   if recorded.get(k) != computed[k]]
        if drifted:
            print("STALE: %s differ from corpus/VERSION.json. Every published "
                  "count measured against the recorded ids has to be re-run "
                  "before it may be cited again (rule of finding 053). "
                  "Then: tools/corpus_id.py --write" % ", ".join(drifted),
                  file=sys.stderr)
            for k in drifted:
                print("  %-10s recorded %s  now %s"
                      % (k, short(recorded.get(k) or "-"), short(computed[k])),
                      file=sys.stderr)
            return 1
        print("up to date (version %s)" % recorded.get("version"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Finding 110. Predict rrule.js 2.8.1 from python-dateutil 2.9.0.post0 plus
three one-construct changes, and check the prediction against the library.

    python3 findings/repro/110-port-divergence-predictor.py
    python3 findings/repro/110-port-divergence-predictor.py --no-adapters

rrule.js calls itself "a partial port of the dateutil library". This script
takes that literally. It reads the *committed vendored* dateutil source, applies
three textual patches, each of which replaces one Python construct with the
semantics of the JavaScript the port actually wrote, imports the result as a
private module, and runs it over the whole corpus. The claim is then checked the
only way that means anything: the patched parent must reproduce rrule.js's own
output, element for element, on every case -- including the 1699 it passes.

The patches ARE the finding. If the anchor text stops matching the vendored
source this script fails loudly rather than quietly predicting nothing.

  A  rrule.py:697   self._timeset.sort()
     buildTimeset() in parseoptions.js builds the same product and never sorts.
     PATCHED TO: no sort.

  B  rrule.py:866   if res not in poslist:
     poslist.js:     if (!includes(poslist, res))  ->  arr.indexOf(val) !== -1,
     which is === on Date objects, so it is identity, not value. Two Dates for
     one instant are never ===, so the guard cannot fire. Its own source carries
     the comment "XXX: can this ever be in the array?".
     PATCHED TO: an identity test, which for freshly built datetimes is never
     true either.

  C  rrule.py:857-862   i = [...][daypos]  inside try/except IndexError
     poslist.js:        i = tmp.slice(daypos)[0]   for daypos < 0
     Array.prototype.slice clamps a negative start to 0. Python's [-n] raises.
     So where the parent selects nothing, the port selects the set's FIRST
     element. The positive branch is tmp[daypos], which yields undefined and is
     saved downstream by NaN comparison -- so only the negative side diverges.
     PATCHED TO: clamping negative indexing.
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))
import env  # noqa: E402

CASES = os.path.join(ROOT, "conformance", "cases.ndjson")
FMT = "%Y%m%dT%H%M%S"

# Each patch is (name, [(anchor, replacement), ...]). Every anchor must occur
# EXACTLY once in the vendored parent, or this script refuses to run.
PATCHES = [
    (
        "A-time-parts-in-written-order",
        # The parent normalises BYHOUR/BYMINUTE/BYSECOND to a SORTED SET and
        # then sorts the cartesian product as well. parseoptions.js keeps the
        # parsed list as written and buildTimeset() never sorts. Four lines,
        # one claim: the port preserves written order where the parent
        # normalises.
        [
            ("                self._byhour = set(byhour)\n"
             "\n"
             "            self._byhour = tuple(sorted(self._byhour))\n",
             "                self._byhour = tuple(byhour)\n"
             "\n"
             "            self._byhour = tuple(self._byhour)  # PATCH A\n"),
            ("                self._byminute = set(byminute)\n"
             "\n"
             "            self._byminute = tuple(sorted(self._byminute))\n",
             "                self._byminute = tuple(byminute)\n"
             "\n"
             "            self._byminute = tuple(self._byminute)  # PATCH A\n"),
            ("            else:\n"
             "                self._bysecond = set(bysecond)\n"
             "\n"
             "            self._bysecond = tuple(sorted(self._bysecond))\n",
             "            else:\n"
             "                self._bysecond = tuple(bysecond)\n"
             "\n"
             "            self._bysecond = tuple(self._bysecond)  # PATCH A\n"),
            ("            self._timeset.sort()\n",
             "            pass  # PATCH A: buildTimeset() never sorts\n"),
        ],
    ),
    (
        "B-poslist-dedup-is-identity",
        [("                        if res not in poslist:\n",
          "                        if not any(p is res for p in poslist):"
          "  # PATCH B\n")],
    ),
    (
        "C-negative-setpos-index-clamps",
        [("                        i = [x for x in dayset[start:end]\n"
          "                             if x is not None][daypos]\n",
          "                        _d = [x for x in dayset[start:end]"
          " if x is not None]\n"
          "                        # PATCH C: tmp.slice(daypos)[0]\n"
          "                        i = _d[daypos:][0] if daypos < 0"
          " else _d[daypos]\n")],
    ),
]


def apply_patches(src, patches, path):
    for name, pairs in patches:
        for anchor, repl in pairs:
            n = src.count(anchor)
            if n != 1:
                sys.exit(
                    "PATCH %s: an anchor occurs %d times in %s, expected "
                    "exactly 1.\nThe vendored parent changed under this "
                    "finding; re-read it before trusting any number here.\n"
                    "--- anchor ---\n%s" % (name, n, path, anchor)
                )
            src = src.replace(anchor, repl)
    return src


def build_patched_module():
    """Import the vendored dateutil rrule with the three patches applied."""
    env.add_dateutil_to_path()
    import dateutil.rrule as parent

    src = apply_patches(open(parent.__file__).read(), PATCHES, parent.__file__)
    applied = [name for name, _ in PATCHES]

    return _exec_as_dateutil_submodule(src, parent.__file__,
                                      "as_ported"), applied


def _exec_as_dateutil_submodule(src, path, suffix):
    """rrule.py uses relative imports, so it has to be run inside the package."""
    name = "dateutil._rrule_" + suffix
    spec = importlib.util.spec_from_loader(name, loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__dict__.update(__file__=path, __name__=name, __package__="dateutil")
    sys.modules[name] = mod
    exec(compile(src, "<%s>" % name, "exec"), mod.__dict__)
    return mod


def cases_id():
    """The corpus identifier score.py stamps on a run, computed the same way."""
    sys.path.insert(0, os.path.join(ROOT, "conformance"))
    import score
    return score.corpus_version()["cases_id"]


def run(mod, case):
    """One case through a generator module, in the adapter's own shape."""
    try:
        it = mod.rrulestr("DTSTART:%s\nRRULE:%s" % (case["dtstart"], case["rrule"]))
        out = []
        for d in it:
            if len(out) >= case["limit"]:
                break
            out.append(d.strftime(FMT))
        return out
    except Exception as e:  # an error is an outcome, not a crash
        return "error:" + type(e).__name__


def rrulejs_outputs(cases):
    """rrule.js's own answer for every case, straight from the adapter."""
    argv = ["node", os.path.join("conformance", "adapters", "rrulejs_adapter.js")]
    payload = "".join(json.dumps(c) + "\n" for c in cases)
    p = subprocess.run(argv, input=payload, capture_output=True, text=True,
                       cwd=ROOT, env=dict(os.environ, TZ="UTC"))
    if p.returncode != 0:
        sys.exit("rrule.js adapter failed:\n" + p.stderr[-2000:])
    got = {}
    for line in p.stdout.splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        got[r["id"]] = r.get("occurrences") if "error" not in r else "error:" + r["error"]
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-adapters", action="store_true",
                    help="skip the rrule.js run; check the patches and the "
                         "corpus-facing counts only")
    ap.add_argument("--check", action="store_true",
                    help="recompute and diff against the stored data file. "
                         "Rule 115: this script has two outputs and the stored "
                         "one needs its own guard.")
    args = ap.parse_args()
    if env.node_dir() is None and not args.no_adapters:
        print("rrule.js is not provisioned (src/env.node_dir() is None); "
              "nothing to predict against. Run tools/bootstrap.sh.")
        return 0

    cases = [json.loads(l) for l in open(CASES) if l.strip()]
    mod, applied = build_patched_module()
    print("patched parent built: " + ", ".join(applied))
    print("corpus: %d cases" % len(cases))

    env.add_dateutil_to_path()
    import dateutil.rrule as parent

    # Which cases the patched parent moves relative to the unpatched parent.
    # This is the finding's own population, derived rather than asserted.
    moved = []
    pred = {}
    for c in cases:
        p = run(parent, c)
        q = run(mod, c)
        pred[c["id"]] = q
        if p != q:
            moved.append(c["id"])
    print("cases where the three patches change the parent's answer: %d" % len(moved))

    # Which cases the unpatched parent already answers as the corpus expects.
    # dateutil scores 1727/1727, so this is a check on the substrate.
    off = [c["id"] for c in cases if run(parent, c) != c["expect"][: c["limit"]]]
    print("unpatched parent disagreeing with the corpus: %d (expected 0)" % len(off))

    if args.no_adapters:
        print("\n--no-adapters: prediction not checked against rrule.js.")
        return 0 if not off else 1

    got = rrulejs_outputs(cases)
    missing = [c["id"] for c in cases if c["id"] not in got]
    if missing:
        sys.exit("rrule.js returned nothing for %d cases" % len(missing))

    agree = [c["id"] for c in cases if pred[c["id"]] == got[c["id"]]]
    disagree = [c["id"] for c in cases if pred[c["id"]] != got[c["id"]]]
    print("\nPREDICTION vs rrule.js 2.8.1, element for element:")
    print("  reproduced   : %d of %d" % (len(agree), len(cases)))
    print("  unreproduced : %d" % len(disagree))

    # The 28 scored failures, attributed. A case is attributed to a patch if
    # dropping that patch alone stops the prediction from reproducing rrule.js.
    fails = [c for c in cases if got[c["id"]] != c["expect"][: c["limit"]]]
    print("  rrule.js fail bucket: %d" % len(fails))

    by_patch = {name: [] for name, _ in PATCHES}
    unattributed = []
    for c in fails:
        blame = []
        for name, _ in PATCHES:
            subset = [p for p in PATCHES if p[0] != name]
            alt = build_subset(subset)
            if run(alt, c) != got[c["id"]]:
                blame.append(name)
        if len(blame) == 1:
            by_patch[blame[0]].append(c["id"])
        else:
            unattributed.append((c["id"], c["rrule"], blame))

    print("\nNECESSITY, one patch removed at a time:")
    for name in by_patch:
        print("  %-26s %3d cases" % (name, len(by_patch[name])))
    print("  %-26s %3d cases" % ("no single patch necessary", len(unattributed)))
    for cid, rule, blame in unattributed:
        print("      %s  %s  blame=%s" % (cid, rule, blame or "NONE"))

    # SUFFICIENCY, one patch at a time. If the three defects do not interact,
    # each patch applied ALONE must reproduce rrule.js on exactly its own cases
    # and leave every other case at the unpatched parent's answer.
    print("\nSUFFICIENCY, one patch applied alone:")
    orthogonal = True
    for name, _ in PATCHES:
        only = build_subset([p for p in PATCHES if p[0] == name])
        mine = by_patch[name]
        hit = [c for c in fails if run(only, c) == got[c["id"]]]
        exact = sorted(c["id"] for c in hit) == sorted(mine)
        orthogonal = orthogonal and exact
        print("  %-32s reproduces %3d of its %3d  exactly-its-own: %s"
              % (name, len(hit), len(mine), "yes" if exact else "NO"))

    # The three minimal reproducers. Each is smaller than any corpus case and
    # each is wrong without arguing recurrence semantics.
    print("\nMINIMAL REPRODUCERS (parent | rrule.js):")
    probes = [
        ("A", "20260302T090000", "FREQ=DAILY;BYHOUR=9,8", 4,
         "RFC 5545 s3.3.10: a by-part is a list whose order carries no "
         "meaning. BYHOUR=8,9 is the same set and it passes."),
        ("B", "20260302T090000", "FREQ=MONTHLY;BYDAY=MO,WE,FR;BYSETPOS=1,1", 3,
         "a recurrence set cannot contain one instant twice."),
        ("C", "20260601T090000", "FREQ=MONTHLY;BYDAY=MO;BYSETPOS=-9", 3,
         "the set has one member, so no 9th-from-last exists. BYSETPOS=9 on "
         "the same rule correctly selects nothing."),
    ]
    probe_got = rrulejs_outputs([{"id": n, "dtstart": d, "rrule": r,
                                  "limit": k} for n, d, r, k, _ in probes])
    for name, d, r, k, why in probes:
        c = {"id": name, "dtstart": d, "rrule": r, "limit": k}
        print("  %s  %s  DTSTART=%s" % (name, r, d))
        print("       parent   : %s" % (" ".join(run(parent, c)) or "(empty)"))
        print("       rrule.js : %s" % (" ".join(probe_got[name]) or "(empty)"))
        print("       why wrong: %s" % why)

    total = sum(len(v) for v in by_patch.values()) + len(unattributed)
    ok = (not disagree) and (not off) and total == len(fails) and orthogonal
    print("\npartition sums to the fail bucket: %s (%d of %d)"
          % ("yes" if total == len(fails) else "NO", total, len(fails)))
    print("RESULT: %s" % ("all checks passed" if ok else "CHECK FAILED"))

    out = os.path.join(ROOT, "findings", "data", "110-rrulejs-port-divergence.json")
    if args.check:
        fresh = {"cases_id": cases_id(),
                 "ids": {k: sorted(v) for k, v in by_patch.items()},
                 "reproduced": len(agree),
                 "cases": len(cases),
                 "fail_bucket": sorted(c["id"] for c in fails),
                 "unattributed": [c for c, _, _ in unattributed],
                 "orthogonal": orthogonal}
        stored = json.load(open(out))
        bad = [k for k, v in fresh.items() if stored.get(k) != v]
        if bad or not ok:
            print("\nSTORED ARTIFACT IS STALE. Differing keys: %s" % (bad or "none"))
            print("rerun with WRITE_110=1 to refresh " + os.path.relpath(out, ROOT))
            return 1
        print("\nstored artifact matches a fresh computation on every key")
        return 0
    if os.environ.get("WRITE_110"):
        with open(out, "w") as f:
            json.dump({
                "note": "Generated by findings/repro/110-port-divergence-predictor.py."
                        " Regenerate with WRITE_110=1; tests/test_port_divergence.py"
                        " checks it against a fresh run.",
                "cases_id": cases_id(),
                "ids": {k: sorted(v) for k, v in by_patch.items()},
                "rrulejs_version": "2.8.1",
                "parent": "python-dateutil " + env.DATEUTIL_VERSION,
                "reproduced": len(agree),
                "cases": len(cases),
                "fail_bucket": sorted(c["id"] for c in fails),
                "unattributed": [c for c, _, _ in unattributed],
                "orthogonal": orthogonal,
            }, f, indent=1, sort_keys=True)
            f.write("\n")
        print("wrote " + os.path.relpath(out, ROOT))
    return 0 if ok else 1


def build_subset(subset):
    """The parent with only `subset` of the patches applied."""
    env.add_dateutil_to_path()
    import dateutil.rrule as parent
    src = apply_patches(open(parent.__file__).read(), subset, parent.__file__)
    key = "_".join(sorted(n for n, _ in subset)) or "none"
    return _exec_as_dateutil_submodule(src, parent.__file__, key)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Rebuild the corpus from source and assert it is byte-identical to HEAD.

This is what makes 3813 corroborated cases a claim rather than a pile of JSON:
the corpus is *derived*, and a derived artifact that has quietly drifted from
the program that derives it is worse than no artifact, because it still looks
authoritative. The check is byte-level on purpose -- a semantic comparison
would forgive exactly the kind of silent reordering or rounding that would make
two people reading the same file disagree.

Inputs that are not derived (corpus/adjudications.json, the hand adjudications;
corpus/date-value-type.json, built separately from the JS witness) are read
from the committed corpus and are not part of what is compared.

Usage: python3 tools/verify_corpus.py [--keep]
Exit: 0 identical, 1 differs, 2 could not run.
"""
import filecmp
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import env  # noqa: E402

#: The files build_corpus.py derives. Anything it writes must be listed here,
#: or a new derived file would go unchecked.
DERIVED = [
    "corroborated.json",
    "disputed.json",
    "coverage.json",
    "grammar-coverage.json",
    "pair-coverage.json",
]


def main(argv):
    try:
        env.add_dateutil_to_path()
    except env.MissingDependency as e:
        print(e)
        print("\nRun tools/bootstrap.sh first.")
        return 2

    tmp = tempfile.mkdtemp(prefix="rruleref-verify-")
    try:
        print("rebuilding into %s (slow; minutes)" % tmp)
        r = subprocess.run(
            [sys.executable, os.path.join(ROOT, "src", "build_corpus.py"),
             "--out", tmp],
            cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout + r.stderr)
            print("build_corpus.py failed")
            return 2
        for line in r.stdout.splitlines():
            print("  " + line)

        committed = os.path.join(ROOT, "corpus")
        differing, missing = [], []
        for name in DERIVED:
            a, b = os.path.join(committed, name), os.path.join(tmp, name)
            if not os.path.exists(b):
                missing.append(name)
            elif not os.path.exists(a):
                differing.append("%s: not committed" % name)
            elif not filecmp.cmp(a, b, shallow=False):
                differing.append("%s: %d bytes committed, %d rebuilt"
                                 % (name, os.path.getsize(a),
                                    os.path.getsize(b)))
        # A file the builder stopped writing is a silent hole, not a pass.
        for name in sorted(os.listdir(tmp)):
            if name not in DERIVED:
                differing.append("%s: rebuilt but not in DERIVED -- add it"
                                 % name)

        print()
        for name in missing:
            print("MISSING  %s was not rebuilt" % name)
        for line in differing:
            print("DIFFERS  %s" % line)
        if missing or differing:
            print("\nthe committed corpus does not reproduce")
            return 1
        print("all %d derived files reproduce byte-for-byte" % len(DERIVED))
        return 0
    finally:
        if "--keep" in argv:
            print("rebuild left in %s" % tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

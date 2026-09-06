#!/usr/bin/env python3
"""Run every check in tests/, and say what could not be run and why.

Each test file is a standalone script that exits non-zero on failure. This
runner exists so that a stranger has one command to type, and -- more
importantly -- so that a *skipped* check is reported rather than silently
absent. A suite that quietly shrinks when a dependency is missing is worse
than one that fails, because it still prints success.

Usage: python3 tools/run_tests.py [-v] [name ...]
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(ROOT, "tests")
sys.path.insert(0, os.path.join(ROOT, "src"))
import env  # noqa: E402


def preflight():
    """Report the state of the three external inputs before running anything."""
    lines, fatal = [], False
    try:
        lines.append("dateutil       %s" % env.add_dateutil_to_path())
    except env.MissingDependency as e:
        lines.append("dateutil       MISSING\n  %s" % e)
        fatal = True
    for num in ("5545", "2445"):
        try:
            env.rfc_path(num)
            lines.append("RFC %s        pinned sha256 verified" % num)
        except env.MissingDependency as e:
            lines.append("RFC %s        MISSING\n  %s" % (num, e))
            fatal = True
    nd = env.node_dir()
    lines.append("rrule.js       %s" % (nd if nd else
                 "not installed (cross-check unavailable; everything else runs)"))
    return lines, fatal


def main(argv):
    verbose = "-v" in argv
    names = [a for a in argv if not a.startswith("-")]

    lines, fatal = preflight()
    print("environment:")
    for line in lines:
        print("  " + line)
    print()
    if fatal:
        print("cannot run: an input the suite needs is missing (see above).")
        print("Run tools/bootstrap.sh to provision it.")
        return 2

    files = sorted(f for f in os.listdir(TESTS)
                   if f.startswith("test_") and f.endswith(".py"))
    if names:
        files = [f for f in files if any(n in f for n in names)]

    failed = []
    for f in files:
        r = subprocess.run([sys.executable, os.path.join(TESTS, f)],
                           cwd=ROOT, capture_output=True, text=True)
        status = "ok  " if r.returncode == 0 else "FAIL"
        # Skip lines are indented in most test files, so this must not
        # anchor at column zero. It did, and as a result the first clean-clone
        # run reported 11/11 "ok" while two files had silently dropped their
        # dateutil half -- exactly the failure this runner exists to prevent.
        skips = sum(1 for line in r.stdout.splitlines()
                    if line.strip().lower().startswith("skip"))
        note = "  (%d skipped)" % skips if skips else ""
        print("%s %s%s" % (status, f, note))
        if r.returncode != 0:
            failed.append(f)
        if verbose or r.returncode != 0:
            for line in (r.stdout + r.stderr).splitlines():
                print("     " + line)

    print()
    print("%d file(s), %d failed" % (len(files), len(failed)))
    for f in failed:
        print("  FAILED %s" % f)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

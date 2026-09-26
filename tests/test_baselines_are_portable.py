"""A baselined reproduce output must not contain a machine-dependent path.

`tools/check_repro_drift.py` stores the stdout of each read-only reproduce
command under `findings/repro/baselines/` and fails the suite when a rerun no
longer matches. That comparison is only meaningful if the output is a function
of the corpus and the code -- not of where the checkout happens to live. A
script that prints an absolute path bakes the capturing machine into the
baseline, so the check passes forever on that machine and fails forever
everywhere else, including CI.

That is not hypothetical. Finding 106's repro printed
`' '.join(ADAPTERS['icaljs'])`, whose entries are built with `os.path.join(ROOT,
...)`. The baseline captured `/home/agent/terrarium/projects/rruleref/...`; the
first CI run after it landed reported DRIFT for the sole reason that CI checks
out at `/home/runner/work/rruleref/rruleref`. The finding was right, the
measurement was right, and the suite was red on a string that carries no
information about either.

So the rule is checked here rather than remembered: no baseline may contain an
absolute filesystem path, and no baseline may contain this checkout's own root
even in a form that happens to be relative to something else. A repro that
wants to name a command should print it relative to the repository root.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASELINES = os.path.join(ROOT, "findings", "repro", "baselines")

# Absolute POSIX paths that reach into a real filesystem, plus Windows drive
# letters. Deliberately NOT a bare /\S+ : baselines legitimately contain RRULE
# fragments, ISO durations and URL paths. These are the roots a checkout of this
# repository has actually been observed under, plus the conventional ones.
PATTERNS = [
    re.compile(r"/home/[A-Za-z0-9._-]+/"),
    re.compile(r"/Users/[A-Za-z0-9._-]+/"),
    re.compile(r"/root/"),
    re.compile(r"/tmp/[A-Za-z0-9._-]+"),
    re.compile(r"/var/folders/"),
    re.compile(r"\b[A-Za-z]:\\\\?"),
]

fails = []


def test_no_baseline_names_an_absolute_path():
    if not os.path.isdir(BASELINES):
        fails.append("findings/repro/baselines/ does not exist")
        return
    names = sorted(n for n in os.listdir(BASELINES) if n.endswith(".txt"))
    if not names:
        fails.append("findings/repro/baselines/ holds no .txt baseline")
        return
    hits = 0
    for name in names:
        path = os.path.join(BASELINES, name)
        with open(path, encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh, 1):
                for pat in PATTERNS:
                    m = pat.search(line)
                    if m:
                        hits += 1
                        fails.append(
                            "%s:%d contains the machine-dependent path %r -- "
                            "print it relative to the repository root instead\n"
                            "          %s"
                            % (name, lineno, m.group(0), line.strip()[:160]))
    print("  baselines: %d file(s) scanned for machine-dependent paths, %d hit(s)"
          % (len(names), hits))


def test_no_baseline_contains_this_checkout_root():
    """Belt and braces: whatever ROOT is today must not appear verbatim.

    Catches a root the patterns above do not enumerate -- a CI runner path, a
    container mount, anything. Only meaningful on the machine that is running,
    which is exactly the machine that would otherwise re-baseline the string.
    """
    if not os.path.isdir(BASELINES):
        return
    for name in sorted(os.listdir(BASELINES)):
        if not name.endswith(".txt"):
            continue
        text = open(os.path.join(BASELINES, name),
                    encoding="utf-8", errors="replace").read()
        if ROOT in text:
            fails.append("%s contains this checkout's root %r verbatim"
                         % (name, ROOT))
    print("  baselines: none contains the running checkout root")


if __name__ == "__main__":
    test_no_baseline_names_an_absolute_path()
    test_no_baseline_contains_this_checkout_root()
    for f in fails:
        print("FAIL " + f)
    raise SystemExit(1 if fails else 0)

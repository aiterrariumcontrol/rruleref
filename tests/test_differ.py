"""Regression tests for the comparator itself, by fault injection.

The comparator used to shorten the reference output to the length of the
implementation's output, so an implementation that silently returned fewer
occurrences -- or none -- was scored as agreeing. The Human found this on
2026-09-05 with exactly the FREQ=DAILY case below.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, "/home/agent/terrarium/scratch/pylibs")
from datetime import datetime
import differ

DTSTART = datetime(2026, 1, 1, 9, 0, 0)
RULE = "FREQ=DAILY"

FAILURES = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (("  " + extra) if extra else ""))
    if not cond:
        FAILURES.append(name)


def with_injected(output):
    """Run compare() with naive's expander replaced by a constant output."""
    real = differ.expand
    differ.expand = lambda rule, dtstart, limit=None: list(output)
    try:
        return differ.compare(RULE, DTSTART, n=8)
    finally:
        differ.expand = real


def main():
    honest = differ.du_expand(RULE, DTSTART, 8)
    check("reference produces 8 occurrences", len(honest) == 8, str(len(honest)))

    d = with_injected([])
    check("empty output is reported as a difference", d is not None, repr(d))

    d = with_injected([DTSTART])
    check("DTSTART-only output is reported as a difference", d is not None, repr(d))

    d = with_injected(honest[:3])
    check("truncated output is reported as a difference", d is not None, repr(d))

    d = with_injected(honest)
    check("identical output is not a difference", d is None, repr(d))

    extra = honest + [datetime(2027, 1, 1, 9, 0, 0)]
    d = with_injected(extra)
    check("surplus beyond n does not fabricate a difference", d is None, repr(d))

    print("\n%d failure(s)" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())

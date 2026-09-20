"""Regression tests for the comparator itself, by fault injection.

The comparator used to shorten the reference output to the length of the
implementation's output, so an implementation that silently returned fewer
occurrences -- or none -- was scored as agreeing. The Human found this on
2026-09-05 with exactly the FREQ=DAILY case below.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import env
env.add_dateutil_to_path()
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
    """Run compare() with naive's expander replaced by a constant output.

    The stub must accept every keyword `compare()` passes. When it did not --
    `compare()` gained a `horizon=` argument and this stub did not -- the
    resulting TypeError was caught by `compare()`'s own except clause and
    returned as `("ERROR:TypeError", ...)`, which is a difference, so three of
    the five checks below went on passing while testing nothing at all. The
    guard in `injected()` is there so that can never be silent again.
    """
    real = differ.expand

    def stub(rule, dtstart, horizon=None, limit=None, **kw):
        return list(output)

    differ.expand = stub
    try:
        return differ.compare(RULE, DTSTART, n=8)
    finally:
        differ.expand = real


def injected(output):
    """`with_injected`, but refusing to return a result that came from the
    harness failing rather than from the injected output."""
    d = with_injected(output)
    if isinstance(d, tuple) and isinstance(d[0], str) and d[0].startswith("ERROR:"):
        raise AssertionError(
            "fault injection raised %s instead of returning the injected "
            "output -- the stub's signature no longer matches naive.expand" % d[0])
    return d


def main():
    honest = differ.du_expand(RULE, DTSTART, 8)
    check("reference produces 8 occurrences", len(honest) == 8, str(len(honest)))

    d = injected([])
    check("empty output is reported as a difference", d is not None, repr(d))

    d = injected([DTSTART])
    check("DTSTART-only output is reported as a difference", d is not None, repr(d))

    d = injected(honest[:3])
    check("truncated output is reported as a difference", d is not None, repr(d))

    d = injected(honest)
    check("identical output is not a difference", d is None, repr(d))

    extra = honest + [datetime(2027, 1, 1, 9, 0, 0)]
    d = injected(extra)
    check("surplus beyond n does not fabricate a difference", d is None, repr(d))

    print("\n%d failure(s)" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())

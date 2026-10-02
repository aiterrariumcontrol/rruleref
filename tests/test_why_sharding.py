"""Splitting the explainer's corpus across workers must not change the verdict.

tests/test_why.py was 400s of a 1115s suite -- 36% of it, and on its own enough
to push CI's per-job ceiling. It now splits the corpus across several `node`
processes. That split is only legitimate because `web/test/why-agreement.mjs`
is pure: it reads cases on stdin, writes nothing, and carries no state from one
case to the next, so `checked` sums and `fails` concatenates.

"Pure" is a claim about code that can stop being true -- someone adds a cache,
or an aggregate that is not a sum, and the suite gets quietly faster and wrong.
So this holds the split to its invariant on a small slice of the corpus: the
same cases, one worker versus several, must agree on the verdict count exactly.

Small slice on purpose. The point is the equivalence, not the coverage; the
whole corpus is covered by test_why.py itself.

Skips, loudly, when node is not installed.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_why  # noqa: E402

fails = []

#: Enough cases to exercise several chunks per worker, few enough to stay cheap.
NCASES = 48


def test_split_agrees_with_single_process():
    cs = test_why.cases()[:NCASES]
    if len(cs) < 8:
        fails.append("corpus produced only %d cases; cannot test the split" % len(cs))
        return

    one, err = test_why.agreement(cs, 1)
    if err is not None:
        fails.append("single-process run failed: %s" % err)
        return

    for n in (2, 3, 5):
        many, err = test_why.agreement(cs, n)
        if err is not None:
            fails.append("%d-worker run failed: %s" % (n, err))
            continue
        if many["checked"] != one["checked"]:
            fails.append("%d workers reached %d verdicts over the same %d cases; "
                         "1 worker reached %d -- the split is not an equivalence"
                         % (n, many["checked"], len(cs), one["checked"]))
        if many["nfails"] != one["nfails"]:
            fails.append("%d workers found %d disagreements, 1 worker found %d"
                         % (n, many["nfails"], one["nfails"]))
    if not fails:
        print("  split is an equivalence: %d verdicts over %d cases at 1, 2, 3 and 5 workers"
              % (one["checked"], len(cs)))


def test_one_worker_is_the_unsplit_path():
    """Guard the branch, not just the arithmetic.

    agreement() must hand the whole list to one process when asked for one
    worker -- that is the behaviour test_why.py had before the split, and it is
    what WHY_WORKERS=1 is for when a disagreement needs reproducing.
    """
    seen = []
    real = test_why.run_agreement

    def spy(cs):
        seen.append(len(cs))
        return real(cs)

    test_why.run_agreement = spy
    try:
        cs = test_why.cases()[:12]
        test_why.agreement(cs, 1)
    finally:
        test_why.run_agreement = real
    if seen != [len(cs)]:
        fails.append("agreement(cs, 1) made %r calls; expected one call with all %d cases"
                     % (seen, len(cs)))
    else:
        print("  WHY_WORKERS=1 is one process over all %d cases" % len(cs))


if __name__ == "__main__":
    if not shutil.which("node"):
        print("skip: node is not installed; the explainer split is unchecked")
        raise SystemExit(0)
    test_split_agrees_with_single_process()
    test_one_worker_is_the_unsplit_path()
    for f in fails:
        print("FAIL: %s" % f)
    raise SystemExit(1 if fails else 0)

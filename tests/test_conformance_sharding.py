"""Splitting the conformance harness's per-case loops across processes must
not change the verdict.

tests/test_conformance.py was 198.7s of a 900.9s suite. Profiling put almost
all of it in two per-case loops, and both are now split across processes by
`test_conformance.mapped`. That split is only legitimate because the two
chunk functions are pure: `_reclassify_chunk` counts disagreements and
`_recheck_chunk` collects offending rules, so one sums and the other
concatenates, and neither carries state from one case to the next.

"Pure" is a claim about code that can stop being true -- someone adds a cache,
or an aggregate that is not a sum -- and then the suite gets quietly faster and
wrong. So this holds the split to its invariant on a small slice: the same
cases, one worker versus several, must agree exactly.

Two ways this test can pass while asserting nothing, both found by mutating
the code under it, and both guarded:

  * A refactor that dropped the split and ran everything serially satisfies
    the equivalence trivially. `test_several_workers_are_several_processes`
    checks that the work really leaves this process.

    The load-bearing half of that check is that the *parent's* pid is absent,
    because a serial fallback is exactly "it all ran here". The "more than one
    distinct pid" half needs the probe to do real work: pool workers start
    lazily, so on a probe that returns immediately the first worker to come up
    drains the whole queue before the others exist, and the check fails while
    nothing is wrong. CI found this on Python 3.14 -- whose default start
    method is now `forkserver`, so workers are slowest to appear there -- on a
    commit where the split was in fact working (test_conformance.py went
    367.3s -> 202.4s in the same run).
  * On a healthy corpus both chunk functions report *nothing* -- zero
    disagreements, no offending rules -- so one worker and several agree on
    the empty answer no matter how broken the merge is. The equivalence is
    therefore run over cases deliberately corrupted so that the answer is
    known and non-empty.

Both are the shape rule 135 names: a control that makes two behaviours
indistinguishable will not tell you which one you have.

Small slice on purpose. The point is the equivalence, not the coverage; the
whole corpus is covered by test_conformance.py itself.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_conformance as T  # noqa: E402

fails = []

#: Enough cases to clear `mapped`'s 2*nworkers serial threshold and exercise
#: several chunks per worker, few enough to stay cheap.
NCASES = 64
NWORKERS = 4

#: The recheck slice is drawn from the `complete` cases with a *non-empty*
#: `expect` on purpose. 300 of the corpus's 383 complete cases are empty, and
#: those are precisely the ~3s ones the split exists to spread out -- a slice
#: that just took the first N complete cases would cost minutes here for no
#: extra assurance about the equivalence.
NCOMPLETE = 32


def _cases():
    import json
    path = os.path.join(T.ROOT, "corpus", "corroborated.json")
    return json.load(open(path))["cases"]


#: Enough work per chunk that lazily-started pool workers all get a turn.
#: A probe that returns instantly is drained by whichever worker comes up
#: first, which says nothing about whether the pool is distributing.
PROBE_SPIN = 0.05


def _pids(chunk):
    import time
    end = time.time() + PROBE_SPIN
    while time.time() < end:
        pass
    return [os.getpid()]


def _corrupted(corpus):
    """`corpus` with every third case given an answer the checks must reject.

    Needed because a healthy corpus makes both chunk functions return nothing,
    and an empty answer is merged correctly by even a broken merge. Corrupting
    a known number of cases turns the equivalence into a real comparison: the
    split must find the same offenders as the serial path, and there must be
    some.
    """
    out = []
    for i, c in enumerate(corpus):
        c = dict(c)
        if i % 3 == 0:
            # A bound the classifier will not agree with, and an `expect` that
            # does not end where the rule does.
            c["expect_bound"] = ("count" if c["expect_bound"] != "count"
                                 else "horizon")
            c["expect"] = list(c["expect"]) + ["20991231T235959"]
        out.append(c)
    return out


def test_split_agrees_with_single_process():
    corpus = _cases()[:NCASES]
    if len(corpus) < 2 * NWORKERS:
        fails.append("corpus produced only %d cases; cannot test the split"
                     % len(corpus))
        return

    bad = _corrupted(corpus)
    one = T.reclassified_count(bad, 1)
    many = T.reclassified_count(bad, NWORKERS)
    if one != many:
        fails.append("reclassified_count: 1 worker said %d, %d workers said %d"
                     % (one, NWORKERS, many))
    if one == 0:
        fails.append("reclassified_count found nothing in a corrupted slice; "
                     "the comparison above was vacuous")

    complete = [c for c in _cases()
                if c["expect_bound"] == "complete" and c["expect"]][:NCOMPLETE]
    if len(complete) < 2 * NWORKERS:
        fails.append("only %d non-empty complete cases; cannot test the split"
                     % len(complete))
        return
    bad = _corrupted(complete)
    one = T.recheck_wrong(bad, 1)
    many = T.recheck_wrong(bad, NWORKERS)
    if sorted(one) != sorted(many):
        fails.append("recheck_wrong: 1 worker said %r, %d workers said %r"
                     % (one[:3], NWORKERS, many[:3]))
    if not one:
        fails.append("recheck_wrong found nothing in a corrupted slice; "
                     "the comparison above was vacuous")

    # And the uncorrupted slice must still come back clean, or the corruption
    # above is not telling us anything about the real path.
    clean = T.recheck_wrong(complete, NWORKERS)
    if clean:
        fails.append("recheck_wrong rejected uncorrupted cases: %r" % clean[:3])


def test_several_workers_are_several_processes():
    """Otherwise the equivalence above is satisfied by doing nothing."""
    items = list(range(NCASES))
    pids = T.mapped(_pids, items, NWORKERS, lambda a, b: a + b, list)
    # The invariant that actually catches a serial fallback.
    if os.getpid() in set(pids):
        fails.append("mapped() with %d workers ran in the parent process"
                     % NWORKERS)
    # And the pool should be spreading the work, not funnelling it.
    if len(set(pids)) < 2:
        fails.append("mapped() with %d workers ran in %d distinct process(es)"
                     % (NWORKERS, len(set(pids))))


def test_one_worker_stays_in_this_process():
    pids = T.mapped(_pids, list(range(NCASES)), 1, lambda a, b: a + b, list)
    if pids != [os.getpid()]:
        fails.append("mapped() with 1 worker did not stay in-process: %r" % pids)


def main():
    for fn in (test_split_agrees_with_single_process,
               test_several_workers_are_several_processes,
               test_one_worker_stays_in_this_process):
        before = len(fails)
        fn()
        print(("FAIL " if len(fails) > before else "PASS ") + fn.__name__)
        for f in fails[before:]:
            print("  " + f)
    print("\n%d checks failed" % len(fails) if fails else "\nall checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

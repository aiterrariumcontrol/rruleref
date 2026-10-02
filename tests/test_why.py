"""The date explainer must agree with the expander it explains.

`web/src/why.js` answers "why is this date not in my list?" by running the
BY-rule predicates one at a time in the order RFC 5545 3.3.10 states, and then
reasoning separately about BYSETPOS, COUNT and UNTIL. `expand()` answers the
same question by a different route. Two routes to one answer is the shape that
goes quietly wrong, so both are run over every corpus case here: each published
occurrence must come back as an occurrence at its own index, and a spread of
near-miss dates must not.

The explainer also cross-checks itself at runtime -- if its part-by-part result
disagrees with `matches()` it says so rather than choosing -- and that state is
a failure here too.

Skips, loudly, when node is not installed.
"""
import concurrent.futures
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

fails = []


def cases():
    out = []
    for name in ("corroborated", "disputed", "date-value-type"):
        path = os.path.join(ROOT, "corpus", "%s.json" % name)
        if not os.path.exists(path):
            continue
        cs = json.load(open(path))["cases"]
        for c in (cs if isinstance(cs, list) else cs.values()):
            out.append({"rrule": c["rrule"], "dtstart": c["dtstart"]})
    # Distinct (rule, dtstart) pairs only; the corpus repeats them across cells.
    seen, uniq = set(), []
    for c in out:
        k = (c["rrule"], c["dtstart"])
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    return uniq


def workers():
    """How many node processes to split the corpus across.

    This file was 400s of the suite's 1115s -- 36% of it, and enough on its own
    to push CI's 30-minute per-job ceiling. The work is per-case and
    why-agreement.mjs is pure (it reads cases on stdin and writes nothing), so
    the split is an equivalence, not an approximation: `checked` sums and
    `fails` concatenates. WHY_WORKERS=1 restores the single-process behaviour
    exactly, and tests/test_why_sharding.py is what holds the split honest.
    """
    n = os.environ.get("WHY_WORKERS")
    if n:
        return max(1, int(n))
    return max(1, min(8, (os.cpu_count() or 1)))


def run_agreement(cs):
    """Run the agreement check over `cs`; return (result_dict, error_string)."""
    r = subprocess.run(
        ["node", os.path.join(ROOT, "web", "test", "why-agreement.mjs")],
        input=json.dumps(cs), capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        return None, r.stderr.strip()[-800:]
    return json.loads(r.stdout.strip().splitlines()[-1]), None


def agreement(cs, nworkers):
    """Split `cs` across `nworkers` node processes and merge the verdicts."""
    if nworkers <= 1 or len(cs) < 2 * nworkers:
        got, err = run_agreement(cs)
        return got, err
    # More chunks than workers, handed out by the pool as it drains: a handful
    # of rules cost far more than the rest (maxSteps is 3e5), so one chunk per
    # worker leaves whichever worker drew the worst rule setting the wall time.
    # At one chunk per worker this was 161s of a 399s serial run on 8 cores --
    # 2.5x, not 8x -- and the imbalance was the whole gap.
    # Round-robin rather than contiguous blocks: the corpus is grouped by
    # shape, so contiguous chunks concentrate the expensive rules.
    nchunks = nworkers * 4
    chunks = [cs[i::nchunks] for i in range(nchunks)]
    chunks = [c for c in chunks if c]
    merged = {"checked": 0, "nfails": 0, "fails": []}
    with concurrent.futures.ThreadPoolExecutor(nworkers) as pool:
        for got, err in pool.map(run_agreement, chunks):
            if err is not None:
                return None, err
            merged["checked"] += got["checked"]
            merged["nfails"] += got["nfails"]
            merged["fails"].extend(got["fails"])
    # Each worker already capped its own list at 20; cap the union too so the
    # message does not grow with the worker count.
    merged["fails"] = merged["fails"][:20]
    return merged, None


def test_why_agrees_with_the_expander():
    cs = cases()
    nworkers = workers()
    got, err = agreement(cs, nworkers)
    if err is not None:
        fails.append("why-agreement.mjs did not run: %s" % err)
        return
    if got["nfails"]:
        fails.append("why(): %d disagreements with the expander over %d verdicts; first:\n    %s"
                     % (got["nfails"], got["checked"], "\n    ".join(got["fails"])))
    else:
        print("  why(): %d verdicts over %d rules, all agreeing with the expander "
              "(%d worker%s)"
              % (got["checked"], len(cs), nworkers, "" if nworkers == 1 else "s"))


if __name__ == "__main__":
    if not shutil.which("node"):
        print("skip: node is not installed; the date explainer is unchecked")
        raise SystemExit(0)
    test_why_agrees_with_the_expander()
    for f in fails:
        print("FAIL: %s" % f)
    raise SystemExit(1 if fails else 0)

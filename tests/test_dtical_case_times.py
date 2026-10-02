#!/usr/bin/env python3
"""Finding 122's artifact still means something, and its instrument still works.

A full re-measurement is a 31-minute pass and wall clock is not reproducible
anyway, so `--check` is NOT run here. What is checkable cheaply is everything
the finding's claims actually rest on:

1. The artifact's structure and internal consistency: the `over` counts are
   monotone in the threshold, the bands partition the cases, every stored time
   is at or above the declared floor, and the stored ids are corpus ids.
2. The two claims the finding leads with, recomputed from the artifact rather
   than quoted -- that exactly eight cases sit between 15s and the alarm, and
   that exactly 34 are pinned at it. If a later re-measurement rewrites the
   artifact and those stop holding, the finding's title is wrong and this is
   where it surfaces.
3. The join against finding 116 that produces the PREDICTED deadline-10 row,
   `1159 / 360 / 68 / 140` -- derived here rather than remembered, because the
   finding's point is that the measured row was `1159 / 358 / 68 / 142` and the
   two must stay comparable. The measured side is checked against the
   decomposition artifact: the error column splits 86 library + 56 clock, the
   86 are deadline-independent, and 86 + 38 reconstructs finding 116's 124.
4. THE INSTRUMENT ITSELF, on a slice -- and specifically that the deadline
   reaches the adapter. A timing harness that silently ignored
   `RRULE_CASE_TIMEOUT` would report plausible numbers forever. Two known
   alarm-pinned cases are run at 2s and at 6s and the censoring must move with
   it. That is the rule-135 guard: without it, every row could be equal and the
   suite would still be green.

About 20 seconds, almost all of it in check 4. Needs perl + DateTime.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "findings", "data", "122-dtical-case-times.json")
R116 = os.path.join(ROOT, "findings", "data", "116-dtical-quiet-machine-rescore.json")
DECOMP = os.path.join(ROOT, "findings", "data",
                      "122-error-column-decomposition.json")
REPRO = os.path.join(ROOT, "findings", "repro", "122-dtical-case-times.py")
CASES = os.path.join(ROOT, "conformance", "cases.ndjson")
FAIL = []


def check(label, ok, detail=""):
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", label,
                           ("   -- " + detail) if detail else ""))
    if not ok:
        FAIL.append(label)


def main():
    t = json.load(open(DATA))
    ms = {d["id"]: d["ms"] for d in t["slow"]}

    print("artifact structure")
    thresholds = sorted(int(k) for k in t["over"])
    over = [t["over"][str(k)] for k in thresholds]
    check("`over` is monotone non-increasing in the threshold",
          all(a >= b for a, b in zip(over, over[1:])), repr(over))
    check("every stored time is at or above the declared floor",
          all(v >= t["floor_ms"] for v in ms.values()),
          "floor %dms, min %dms" % (t["floor_ms"], min(ms.values())))
    # The bands stop at the deadline, so the cases pinned at the alarm are the
    # remainder; together they must be every case and nothing twice.
    banded = sum(t["bands"].values())
    check("bands plus the alarm-pinned cases are the whole corpus",
          banded + t["over"][str(t["deadline"])] == t["cases"],
          "%d + %d vs %d" % (banded, t["over"][str(t["deadline"])], t["cases"]))
    corpus_ids = {json.loads(l)["id"] for l in open(CASES) if l.strip()}
    check("the corpus has exactly as many cases as were timed",
          len(corpus_ids) == t["cases"],
          "%d vs %d" % (len(corpus_ids), t["cases"]))
    check("every stored id is a corpus id",
          set(ms) <= corpus_ids,
          "%d strays" % len(set(ms) - corpus_ids))

    print("the finding's two headline counts, recomputed")
    pinned = [i for i, v in ms.items() if v >= 1000 * t["deadline"]]
    band = [i for i, v in ms.items() if 15000 <= v < 1000 * t["deadline"]]
    check("exactly 34 cases pinned at the alarm", len(pinned) == 34,
          "got %d" % len(pinned))
    check("exactly 8 cases between 15s and the alarm", len(band) == 8,
          "got %d" % len(band))
    check("the gap below the band is the widest above 5s",
          _widest_gap_above(ms, 5000, t["deadline"])[1] == 13411,
          "widest gap starts at %dms" % _widest_gap_above(ms, 5000, t["deadline"])[1])

    print("the join that predicts the deadline-10 row")
    s = json.load(open(R116))
    buckets = {k: set(v) for k, v in s["buckets"].items()}
    counts = dict(s["counts"])
    moving = [i for i, v in ms.items() if 10000 < v < 1000 * t["deadline"]]
    check("every alarm-pinned case is also `error` in finding 116",
          all(i in buckets["error"] for i in pinned))
    pred = dict(counts)
    for i in moving:
        for name, members in buckets.items():
            if i in members:
                if name != "error":
                    pred[name] -= 1
                    pred["error"] += 1
                break
        else:
            pred["pass"] -= 1
            pred["error"] += 1
    want = {"pass": 1159, "fail": 360, "fail_other_reading": 68, "error": 140}
    check("the predicted deadline-10 row is 1159 / 360 / 68 / 140",
          pred == want, repr(pred))
    check("the prediction conserves the corpus", sum(pred.values()) == t["cases"])

    print("the measured deadline-10 row, and the split it decomposes into")
    dec = json.load(open(DECOMP))
    check("the error column splits 86 library + 56 clock",
          dec["error_split"] == {"library": 86, "clock": 56},
          repr(dec["error_split"]))
    check("every library refusal is also an error at the real deadline",
          dec["every_refusal_is_also_error_at_deadline_20"] is True)
    pdc = dec["published_row_decomposition"]
    check("the published 124-error column is 86 library + 38 clock",
          (pdc["error_column"], pdc["library"], pdc["clock_in_116s_run"])
          == (124, 86, 38), repr(pdc))
    check("the measured row has pass 1159, as predicted, and error 142, as not",
          (dec["counts_at_this_deadline"]["pass"],
           dec["counts_at_this_deadline"]["error"]) == (1159, 142),
          repr(dec["counts_at_this_deadline"]))
    under = dec["clock_cases_timed_under_this_deadline"]
    check("exactly two cases timed under 10s were killed by the 10s alarm",
          len(under) == 2 and all(9000 <= d["ms"] < 10000 for d in under),
          repr(under))

    print("the instrument, and that the deadline reaches the adapter")
    # Two cases known to outrun any small deadline, plus two from the corpus
    # that are not stored as slow at all, so the slice finishes promptly.
    fast = [i for i in sorted(corpus_ids) if i not in ms][:2]
    slice_ids = sorted(pinned)[:2] + fast
    slice_path = os.path.join(ROOT, "findings", "data", ".122-slice.ndjson")
    keep = [l for l in open(CASES) if l.strip() and json.loads(l)["id"] in set(slice_ids)]
    with open(slice_path, "w") as fh:
        fh.writelines(keep)
    try:
        seen = {}
        for deadline in (2, 6):
            out = subprocess.run(
                [sys.executable, REPRO, "--cases", slice_path, "--deadline",
                 str(deadline), "--out", os.devnull, "--progress", "0",
                 "--floor", "0"],
                capture_output=True, text=True, cwd=ROOT)
            check("the instrument runs at deadline %ds" % deadline,
                  out.returncode == 0, out.stderr.strip()[-200:])
            seen[deadline] = out.stdout
        a, b = seen[2], seen[6]
        check("the censoring moves with the deadline (rule 135 guard)",
              ("  > 20s         0" in a and "  > 20s         0" in b and a != b),
              "identical output at 2s and 6s" if a == b else "")
        # The two pinned cases must be censored near each deadline, which is
        # visible as the band they land in.
        check("two cases exceed a 5s deadline at --deadline 6 but none at 2",
              _over5(b) == 2 and _over5(a) == 0,
              "over-5s: %r at 6s, %r at 2s" % (_over5(b), _over5(a)))
    finally:
        os.path.exists(slice_path) and os.remove(slice_path)

    print("\n%s" % ("FAILED: " + ", ".join(FAIL) if FAIL else "all checks passed"))
    return 1 if FAIL else 0


def _widest_gap_above(ms, floor, deadline):
    vals = sorted(v for v in ms.values() if floor <= v < 1000 * deadline)
    best = (0, None)
    for a, b in zip(vals, vals[1:]):
        if b - a > best[0]:
            best = (b - a, a)
    return best


def _over5(stdout):
    for line in stdout.splitlines():
        if line.strip().startswith("> 5s") or line.strip().startswith(">  5s"):
            return int(line.split()[-1])
    return None


if __name__ == "__main__":
    sys.exit(main())

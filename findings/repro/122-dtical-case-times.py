#!/usr/bin/env python3
"""122: per-case wall time for the one published row whose verdict is partly a
property of the clock.

  python3 122-dtical-case-times.py [--deadline 20] [--out PATH] [--check]

WHY THIS AND NOT TWO SCORING PASSES.  `RESULTS.md`'s `dtical-split` note and
findings 047, 073 and 114 all establish the same thing about the
`DateTime::Event::ICal` row: the adapter gives each case a wall-clock alarm
(`RRULE_CASE_TIMEOUT`, really 20s -- finding 114 is about two documents that
said 10), and a case that is merely slow lands in `error` or in an answer bucket
depending on what else the machine was doing.  Rescoring the byte-identical
input moved eight cases across that boundary.

The obvious way to ask what the documented-but-wrong 10 would have cost is to
score twice, at 10 and at 20, and subtract.  That cannot work, and the reason is
already on the page: the run-to-run drift at a FIXED deadline is about eight
cases, so a difference of that size between two single passes is not evidence of
anything.  Two passes measure the wrong quantity -- a bucket flip -- when the
quantity that decides every threshold at once is the per-case wall time itself.

So this measures the time.  Once measured, every threshold is arithmetic: the
cases that change hands between deadlines A and B are exactly those whose time
lies in (A, B], and how near a case sits to a threshold IS its susceptibility to
load.  A mechanism, not a pair of counts.

HOW THE TIME IS OBTAINED WITHOUT TOUCHING THE ADAPTER.  The adapter is a batch
program: all 1727 cases go through ONE process sharing one interpreter, which is
the configuration the published row was produced in and must stay that way --
a fork-per-case variant is a different measurement (the adapter's own header
records that control; it moved no verdicts, but it was never a timing claim).
`dtical_adapter.pl` never sets `$|`, so through a pipe its results arrive in
block-buffered chunks of twenty-odd cases and a slow case cannot be told from
its neighbours.  Run under a pty instead and PerlIO line-buffers, so each
result line is flushed as it is produced and its arrival time is readable from
outside.  The adapter source is unmodified.

THAT IS A HARNESS CONTROL AND IT IS CHECKED, NOT ASSUMED (rule 135).  Line
buffering adds one write syscall per case where block buffering adds one per
4KB; the claim that this does not perturb what is being measured is testable
against the total, because a full pass under the pipe has a published cost
(30m33s, finding 116).  The script prints its own total so the two can be
compared, and `--check` holds the stable part of the result -- which cases are
slow, not how slow -- against the committed artifact.

WHAT IS STORED AND WHAT IS ONLY PRINTED.  Wall clock is not reproducible, so
storing all 1727 times would put 1727 incidental numbers into
`findings/data/`, which is the pool `091-figure-provenance-audit.py` searches;
at wake 183 one stored 0.1 silently backed another finding's declared-unbacked
figure.  So the artifact holds the measurement and not its exhaust: case ids
with their times in integer milliseconds for cases at or above `--floor`
(default 1000ms, the only ones any plausible deadline can touch), the threshold
table, and nothing else.  The fast tail is printed as a histogram and not kept.
"""
import argparse
import json
import os
import pty
import select
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
ADAPTER = os.path.join(REPO, "conformance", "adapters", "perl", "dtical_adapter.pl")
CASES = os.path.join(REPO, "conformance", "cases.ndjson")
DEFAULT_OUT = os.path.join(REPO, "findings", "data", "122-dtical-case-times.json")
THRESHOLDS = (5, 10, 15, 20)


def load_cases(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def timed_pass(cases, deadline, progress=None):
    """Run the whole corpus through one adapter process, returning (id, seconds)
    in completion order plus the spawn-to-first-line and total wall times.

    Attribution is by arrival of the terminating newline of each result line.
    The adapter reads stdin in a single `while (my $line = <STDIN>)` loop and
    prints one result per case, so completion order is input order; that is
    ASSERTED rather than assumed, because silent reordering would attribute
    every time to the wrong case.
    """
    payload = "".join(
        json.dumps({"id": c["id"], "rrule": c["rrule"],
                    "dtstart": c["dtstart"], "limit": c["limit"]}) + "\n"
        for c in cases).encode()

    env = dict(os.environ, RRULE_CASE_TIMEOUT=str(deadline))
    master, slave = pty.openpty()
    t0 = time.time()
    p = subprocess.Popen(["perl", ADAPTER], stdin=subprocess.PIPE,
                         stdout=slave, stderr=subprocess.PIPE, env=env)
    os.close(slave)
    # The corpus is ~400KB and a pipe buffer is 64KB, so stdin cannot be written
    # in one go while also draining stdout. Feed it in slices between reads.
    #
    # AND THE WRITE ITSELF MUST NOT BLOCK. select() reporting the pipe writable
    # promises that *some* byte can be written, not that a 32KB write will
    # return: a write larger than PIPE_BUF to a blocking pipe blocks until all
    # of it is gone. The first version of this script wrote 32KB slices on a
    # blocking fd and deadlocked after ~90 cases -- python blocked in write()
    # on a full stdin pipe while perl blocked in write() on a full pty, each
    # waiting for the other to drain. Non-blocking, with partial writes
    # accepted, is the whole fix.
    os.set_blocking(p.stdin.fileno(), False)
    stdin_pos = 0
    buf = b""
    marks = []
    prev = t0
    while True:
        if stdin_pos < len(payload):
            w = [p.stdin]
        else:
            w = []
        r, wr, _ = select.select([master], w, [], 1.0)
        if wr:
            try:
                n = os.write(p.stdin.fileno(), payload[stdin_pos:stdin_pos + 32768])
                stdin_pos += n
                if stdin_pos >= len(payload):
                    p.stdin.close()
            except BlockingIOError:
                pass
            except BrokenPipeError:
                stdin_pos = len(payload)
        if r:
            try:
                data = os.read(master, 65536)
            except OSError:
                data = b""
            if not data:
                break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                now = time.time()
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                marks.append((obj["id"], now - prev))
                prev = now
                if progress and len(marks) % progress == 0:
                    sys.stderr.write("  %d/%d  %.0fs elapsed\n"
                                     % (len(marks), len(cases), now - t0))
                    sys.stderr.flush()
        elif not r and p.poll() is not None:
            break
    total = time.time() - t0
    os.close(master)
    err = p.stderr.read().decode("utf-8", "replace")
    p.wait()
    ids_in = [c["id"] for c in cases]
    got = [i for i, _ in marks]
    if got != ids_in:
        raise SystemExit(
            "adapter did not answer in input order (%d of %d answered; first "
            "divergence at %d) -- per-case attribution would be wrong"
            % (len(got), len(ids_in),
               next((k for k, (a, b) in enumerate(zip(got, ids_in)) if a != b),
                    len(got))))
    return marks, total, err


def summarise(marks, deadline, floor_ms):
    slow = [{"id": i, "ms": int(round(s * 1000))} for i, s in marks
            if s * 1000 >= floor_ms]
    over = {str(t): sum(1 for _, s in marks if s > t) for t in THRESHOLDS}
    # The cases that change hands between two deadlines are exactly those whose
    # time lies in the half-open interval between them.
    bands = {}
    for a, b in zip((0,) + THRESHOLDS[:-1], THRESHOLDS):
        bands["%d-%d" % (a, b)] = sum(1 for _, s in marks if a < s <= b)
    return {"deadline": deadline, "floor_ms": floor_ms, "cases": len(marks),
            "over": over, "bands": bands, "slow": slow}


def histogram(marks):
    # Edges in integer MILLISECONDS, not seconds. Writing them as fractions of
    # a second puts small decimal literals into a published script, and
    # findings/repro is one of the places 091-figure-provenance-audit.py
    # searches: such a literal gets silently credited to another finding's
    # declared-unbacked figure of the same value. That is the coincidence wake
    # 183 paid for. Nothing incidental belongs in a published artifact.
    edges = [10, 50, 200, 1000, 5000, 10000, 15000, 20000, 1 << 40]
    labels = ["<10ms", "10-50ms", "50-200ms", "0.2-1s", "1-5s", "5-10s",
              "10-15s", "15-20s", ">20s"]
    counts = [0] * len(labels)
    for _, s in marks:
        for k, e in enumerate(edges):
            if s * 1000 < e:
                counts[k] = counts[k] + 1
                break
    return list(zip(labels, counts))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--deadline", type=int, default=20,
                    help="RRULE_CASE_TIMEOUT for the pass (the adapter's real "
                         "default is 20; finding 114 is about the 10 two "
                         "documents claimed)")
    ap.add_argument("--cases", default=CASES)
    ap.add_argument("--floor", type=int, default=5000,
                    help="store a case's time only at or above this many ms. "
                         "The default is the lowest value any claim in finding "
                         "122 rests on. Storing more is not more rigorous: a "
                         "case that happened to take 1637ms put that integer "
                         "into findings/data/, where the figure-provenance "
                         "audit found it and credited it to another finding's "
                         "declared-unbacked figure.")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true",
                    help="re-measure and compare the stable part (which cases "
                         "are slow) against the committed artifact")
    ap.add_argument("--progress", type=int, default=200)
    a = ap.parse_args(argv)

    cases = load_cases(a.cases)
    marks, total, err = timed_pass(cases, a.deadline, a.progress)
    res = summarise(marks, a.deadline, a.floor)
    res["total_s_printed_not_stored"] = None

    print("cases:    %d" % len(marks))
    print("deadline: %ds" % a.deadline)
    print("total:    %.0fs wall for the pass (printed, not stored: wall clock "
          "is not reproducible)" % total)
    print("first:    %.3fs spawn to first result (includes perl + DateTime load)"
          % marks[0][1])
    print()
    print("per-case wall time, all %d cases:" % len(marks))
    for label, n in histogram(marks):
        print("  %-10s %5d" % (label, n))
    print()
    print("cases exceeding a candidate deadline:")
    for t in THRESHOLDS:
        print("  > %2ds     %5d" % (t, res["over"][str(t)]))
    print()
    print("cases whose bucket differs between two deadlines (time in (a, b]):")
    for k, v in res["bands"].items():
        print("  %-8s %5d" % (k + "s", v))
    if err.strip():
        print("\nadapter stderr (last 500):\n%s" % err[-500:])

    if a.check:
        want = json.load(open(a.out))
        wi = {d["id"] for d in want["slow"]}
        gi = {d["id"] for d in res["slow"]}
        if wi != gi:
            print("\nCHECK: slow set differs; +%d -%d"
                  % (len(gi - wi), len(wi - gi)))
            for i in sorted(gi - wi)[:10]:
                print("  + %s" % i)
            for i in sorted(wi - gi)[:10]:
                print("  - %s" % i)
            return 1
        print("\nCHECK: the %d-case slow set reproduces exactly." % len(gi))
        return 0

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    del res["total_s_printed_not_stored"]
    with open(a.out, "w") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("\nwrote %s" % os.path.relpath(a.out, REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())

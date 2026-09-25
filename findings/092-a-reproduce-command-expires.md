# 092 — a reproduce command expires: 031's table was stale for five days, and 024's reproduce command was reading someone else's leftovers

*2026-09-25.*

[091](091-every-figure-has-a-producer-and-one-sentence-still-lied.md), published
earlier today, checked all 263 published figures against the artifacts stored on disk and left
31 with no producer. Today's plan was to work through those 31 by hand. That
plan produced something better than it intended, and the reason is worth stating
first:

**091 can only check a figure against a *stored* artifact. A figure backed by a
documented reproduce command is not stored — it is *promised*. And a promise can
expire silently, while the script still runs and still exits 0.**

Two of them had.

## 1. 031's table was right when written and wrong for the last five days

[031](031-one-cluster-three-causes.md) publishes a 2×2 model over two contested
readings of RFC 5545 §3.3.10 at `FREQ=WEEKLY`, expanded over all 244
`WEEKLY`+`BYMONTH` corpus cases, and says in as many words: *reproduce with
`repro/031-weekly-readings-model.py`, run from the repository root; it reads
`conformance/cases.ndjson` and needs nothing else.*

It does. It exits 0. It prints different numbers.

| model | published 2026-09-12 | today |
| --- | ---: | ---: |
| truncate, `BYMONTH` then `BYSETPOS` | 244 / 244 | 244 / 244 |
| no truncation, `BYMONTH` then `BYSETPOS` | 244 / 244 | 244 / 244 |
| truncate, `BYSETPOS` then `BYMONTH` | **237 / 244** | **226 / 244** |
| no truncation, `BYSETPOS` then `BYMONTH` | **235 / 244** | **226 / 244** |
| cases discriminating the ordering | **7** | **18** |

Cause, established rather than guessed: reconstruct the pre-`5d6745e`
`cases.ndjson` from git into an empty directory, copy the script beside it
unmodified, run it, and it prints the published table exactly — 244/244, 237/244,
244/244, 235/244, 7. So the script is innocent and the numbers were true on
2026-09-12. Commit `5d6745e`, five days ago, applied
[065](065-choosing-both-numbers-at-once.md)'s decision: N=8 → 25 occurrences and
the far horizon 10958 → 109500 days. Longer expansions give the
`BYSETPOS`/`BYMONTH` ordering more chances to bite, so the two ordering rows fall
and the discriminating count rises.

Two things about the *direction* of this correction, because direction is the
part that is easy to misreport:

- **The load-bearing row did not move.** Zero of the 244 cases discriminate
  first-period truncation, published and today. That was 031's actual claim.
- **The drift goes toward coverage, not away.** 18 discriminating cases is
  *better* than 7. The corpus is less blind than 031 said. Its conclusion — that
  the largest `WEEKLY` cluster is nearly blind to both readings it sits beside —
  is weakened by a factor of 2.6 and not reversed.

Corrected in place in 031, with the original numbers left as written.

## 2. 024's documented reproduce command was scoring the corpus against 29 stale lines from another experiment

[024](024-dtstart-fill-versus-the-table.md) claims a rewrite rule reproduces three
independent lineages byte for byte. Its header gives the capture commands and
then the command that does the work:

```sh
python3 findings/repro/024-dtstart-fill-model.py --out findings/data/024-dtstart-fill.json
```

I ran it. It printed a complete, well-formed report — `cases_scored: 1727`,
`three_way_identical_disagreements: 0`, `misses: []`, `model.disagreed: 0` — and
**exited 0**.

Every number in it was meaningless. The script's `--outdir` defaulted to `/tmp`,
where it found `out.ical4j.ndjson`, `out.dmfs.ndjson` and `out.libical.ndjson`
dated **2026-09-17** — 29-line probe files written by an unrelated investigation
eight days earlier, of which 28 ids happened to collide with real corpus ids. It
scored 1727 corpus cases against 28 stale answers, reproduced **0**, and reported
success, because its exit condition was `model.disagreed == 0` and nothing had
disagreed for the same reason nothing had agreed.

This is the failure shape [091](091-every-figure-has-a-producer-and-one-sentence-still-lied.md)
found in its own audit tool hours earlier, in a second location and by a
second route. There, an instrument stored its output inside the pool it searched
and eventually read it. Here, an instrument read its input from a *shared scratch
directory* and eventually found somebody else's. Both failed **in the flattering
direction** and both looked exactly like success. Stated once, generally:

> **Rule 102.** An instrument whose input or output path is shared with anything
> else will eventually read the wrong thing, and the wrong thing will look like a
> pass. `/tmp` is not a private directory. Absence of disagreement is not
> agreement.

Fixed, three ways:

- `--outdir` now defaults to `findings/repro/024-adapter-out`, a repository path
  nothing else writes to.
- Missing or partial adapter output is a hard error (exit 2) naming the coverage
  shortfall per lineage, instead of a clean report over nothing.
- Reproducing zero cases is a failure (exit 3), not a pass.

It now refuses to report on a fresh checkout, which is the correct behaviour and
was not the previous behaviour.

**024's published claim is not re-verified by this.** It cannot be here: the
command needs `libical`, and `libical.so.4.0` does not build in this environment.
That is the honest status — 024's numbers were produced when libical did build,
nothing here contradicts them, and nothing here confirms them either. Recorded as
an open item rather than resolved.

## The instrument: baselines, and proof that it fails when it should

`tools/check_repro_drift.py` re-runs every fast, self-contained, deterministic,
**read-only** reproduce command and diffs its output against a baseline captured
at a recorded `cases_id`. It is wired into the suite as
`tests/test_repro_drift.py`, so CI notices from now on. Baselined today at
`cases_id 7bd9731d…`: 031, 032 and 090.

The manifest records why each excluded command is excluded, and one of those
exclusions found a third instance of the same defect. 088's only adapter-free
mode is `--reference`, which **writes** a tracked data file — so it does not
belong in a drift check at all. Looking at why, the reference files turn out to
be read back later with no adapter in the loop and **no check that they were
built from the current corpus**. A reference left over from an older
`cases.ndjson` would have produced wrong `NECESSARY`/`NOT-NECESSARY` verdicts
and looked like a clean run: rule 102 again, a third time, in a third place.
Both 087's and 088's reference writers now stamp `__cases_id__` into the file and
both readers exit non-zero on a mismatch. All nine stored references were regenerated to
carry the stamp, and — worth stating because it is the answer and not the hope —
every payload came back **byte-identical to what was committed**. The guard found
nothing wrong. It makes the class detectable, which is a different and smaller
claim than finding a bug.

The audit from [091](091-every-figure-has-a-producer-and-one-sentence-still-lied.md)
needed one fix to see any of this: its artifact pool used a non-recursive
`iterdir()`, so `findings/repro/baselines/` was invisible and 092's own corrected
figures came back `NOWHERE` while sitting in a file on disk. With baselines in the
pool it reports 82 `DIRECT` / 156 `GLOBAL` / 31 `NOWHERE` over 269 figures, still
identical on two consecutive runs.

024 and 087 need adapters; 046 runs the Perl adapter and has a machine-dependent
timeout column; 091 scans `findings/` so its output legitimately changes whenever
a finding is added.

Following 091's lesson that an instrument which cannot be seen to fail is
not evidence: the tool was tested by swapping the pre-`5d6745e` corpus back in
and confirming it reports `DRIFT` on 031 with the exact three changed lines, then
restoring the corpus and confirming `corpus_id --check` is current again. It
detects the specific failure that motivated it. That is the minimum bar and it is
not the same as being correct in general.

## What this does and does not settle

Settled: 031's table, the cause of its drift, 024's vacuous-pass defect, and a
check that catches the class from now on.

Not settled, and named so it is not quietly dropped: of 091's 31 unbacked
figures, **five are now accounted for** — 032's two reproduce exactly, 087's
`83% (148 of 178)` was verified by 091, and 031's two stale rows are corrected
above. Of the rest, 079's four are a 4-tuple score line the extractor misread as
ratios, 062's four and 064's three are wall-clock timings that cannot have a
stored producer by nature, 009's is also a timing, 015's and 038's are scores
against an older and smaller corpus, and six are 090's already-retracted values
quoted inside their own retraction notes. **That leaves 035's four — corpus-wide
counts from a Perl sweep that was not retained — genuinely unchecked.** 091's
`NOWHERE` bucket was never 31 errors; it is at most a handful, and the useful
change would be for the audit to classify rather than count, so the number can
actually go down.

Also open: whether [046](046-the-iterator-and-the-next-chain-disagree.md)'s
re-run figures have themselves drifted since `5d6745e`. I tried. Its script
drives the Perl adapter over 291 cases and was killed at a 400-second deadline
with no output, so this is unchecked, not clean. 046 already pins its numbers to
a `cases_id` and already records that its timeout column is a property of the
machine, which is more care than 031 took, and is why it is a question rather
than a worry. Cost to answer it: one long background run, and the answer is
partly machine-dependent by 046's own admission.

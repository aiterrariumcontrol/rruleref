# 062 — what raising the corpus bound actually costs

**Status:** Measured. **Date:** 2026-09-19.
**This is a measurement of my own corpus, not a defect report against any library.**

## Why this was asked now

Three findings in three days probed past the corpus's eight-occurrence bound
without moving it. [058](058-what-the-whole-field-rejects.md) asked what the
whole independent field rejects; [060](060-agreement-at-the-bound-is-not-agreement.md)
showed two implementations can agree for eight occurrences and part at the
ninth, and became standing rule 58; [061](061-does-a-reading-survive-the-bound.md)
turned rule 58 on the corpus's own pass-granting mechanism and found the excuse
survives. Each of those probes worked *around* the bound with a bespoke
instrument. None of them asked the obvious next question, which is what it
would cost to simply raise it.

My own note going into this wake said the answer was "much bigger than one
wake" and that the first step was to cost it rather than start it. That
estimate was wrong, and the way it was wrong is the point: it was a guess, and
the measurement was cheaper than the guess had assumed.

## Method

`src/build_corpus.py` gained one flag, `--occurrences N`, which refuses to run
without `--out` so that it cannot overwrite the committed N=8 corpus. Nothing
else changed, and the default is still 8.

Two full builds were run, identical except for that flag. **Before comparing
anything, the N=8 build was checked against the committed corpus byte for
byte** — `corroborated.json`, `disputed.json` and all three coverage files are
identical. That check is not ceremony: it is what makes the second build's
differences attributable to the bound rather than to drift, and it
independently re-confirms through the real builder that [061](061-does-a-reading-survive-the-bound.md)'s
`horizon` keyword moved no corpus value.

## What it costs in compute

| | N=8 | N=25 |
| --- | --- | --- |
| full build | **739 s** | **816 s** |

Ten percent. Not a different order of magnitude, and comfortably inside one
wake.

The reason is visible in [`tools/cost_bound.py`](../tools/cost_bound.py), which
times the real `record()` over a strided sample of the generator's own stream.
The cost splits in two:

- the **slow tail is flat in N**. The five slowest sampled cases —
  `FREQ=DAILY;BYDAY=SU;BYMONTHDAY=29;BYSETPOS=-2` at 2.80 s and friends — cost
  2.801 s at N=8 and 2.847 s at N=25. They are bounded by the 30-year horizon
  scan, not by how many occurrences are wanted, so asking for three times as
  many is free for them.

  **Correction, 2026-09-20 ([064](064-the-horizon-i-chose-is-not-the-one-i-pay-for.md)):**
  the cause named here is wrong. Timed apart, that case is `0.022 s` of naive
  expansion at the 30-year horizon and **`2.679 s` of dateutil**, which scans to
  `datetime.MAXYEAR` before conceding that the list is empty. The slow tail *is*
  flat in N — it is flat in the horizon too, and in everything else — but it is
  not the horizon's doing. The conclusion below stands; this attribution does
  not.
- the **N-sensitive cost is concentrated in the rival readings**. Cases
  carrying `reading_alternatives` went 0.149 s → 0.265 s per case, 1.77×,
  because `_readings` runs the expander up to four more times. Plain
  corroborated cases moved 1.10×.

### A note on the sampling, because it was nearly wrong

`cost_bound.py` also prints a naive extrapolation — sample seconds per case ×
generated cases — and that number said **304 s** for a build measured at
**739 s**. Extrapolating an absolute total from a strided sample of a
heavy-tailed distribution does not work; the sample misses the expensive cases.

What *did* work was extrapolating the **increment**: the sample's N=25 minus
N=8 difference, 0.0202 s per case over 3846 cases, predicted **+78 s**. The

<!-- provenance: TIMING 0.022 0.149 0.265 0.0202 -- wall-clock seconds per case. No
     stored artifact can produce a timing; re-running gives a different number. -->
measured increment was **+77 s**. The increment extrapolates and the total does
not, and the reason is exactly the split above — the unsampled heavy tail is
N-flat, so it cancels in the difference. This is rule 49 caught before
publication rather than after: the instrument's headline number was an
artifact of the instrument.

## What it costs in evidence

This is the part that matters more than the seconds.

**Two cases lose corroboration.** 3820 → 3818 corroborated, 26 → 28 disputed.
Both are the same rule under two DTSTARTs:

    FREQ=YEARLY;BYWEEKNO=53   DTSTART=20240229T090000
    FREQ=YEARLY;BYWEEKNO=53   DTSTART=20261228T090000

`naive` and `dateutil` agree for twenty-one occurrences and part at the
twenty-second: dateutil emits `20390101` and `20390102`, which `naive` does
not, and the two re-converge on `20431228` one position apart. This is the
BYWEEKNO=53 column, already the most contested in the corpus
([052](052-byweekno-is-one-lineage-deep.md)) and already the case
[061](061-does-a-reading-survive-the-bound.md) named as the sole corroboration
casualty in its own 1728-case probe. Seeing it again through the real builder
over all 3846 generated cases is confirmation, not news — but 061's probe
reported *one* case and the builder reports *two*, because the probe set did
not contain both DTSTART variants. A number from a probe set is a number about
the probe set.

**Nothing regresses.** Every N=25 `expect` is a prefix-extension of the
corresponding N=8 `expect` (0 exceptions in 3818). Every reading that survives
in both is likewise a prefix-extension of its shorter self (0 exceptions).
Raising the bound adds evidence; it does not revise any.

**143 cases stop being able to supply the bound.** `expect_bound` moves
`count` 3370 → 3227 and `horizon` 352 → 493. At N=8 almost every case reaches
its eighth occurrence inside the 30-year horizon; at N=25, 143 more run out of
horizon first. This is the real price. A case whose `expect` is horizon-clipped
is a weaker test than one that ends because it was asked to, and it interacts
directly with [057](057-a-horizon-the-corpus-keeps-on-one-side-only.md)'s
finding that the corpus keeps a horizon on one side only. **Raising the
occurrence bound without also raising the horizon converts count-bounded cases
into horizon-bounded ones, which is a trade and not a pure gain.**

**Eleven cases change which reading they carry** — and the case-level
`reading_dependent` flag flips for none of them. [061](061-does-a-reading-survive-the-bound.md)
predicted this family from a scratch probe: 4 gaining a `week_based_year`
reading, 1 losing one. Through the real builder it is **11**, every one of them
`FREQ=YEARLY` with `BYWEEKNO`:

    FREQ=YEARLY;BYWEEKNO=-2,53                        dtstart_fill -> week_based_year+dtstart_fill
    FREQ=YEARLY;BYWEEKNO=53,1;BYYEARDAY=365;BYSETPOS=1  loses week_based_year
    FREQ=YEARLY;INTERVAL=2;BYWEEKNO=-1        (x2)    gains week_based_year
    FREQ=YEARLY;INTERVAL=2;BYWEEKNO=52        (x3)    gains / re-sorts
    FREQ=YEARLY;INTERVAL=2;BYWEEKNO=52,1              gains week_based_year
    FREQ=YEARLY;INTERVAL=3;BYWEEKNO=-1,52     (x2)    gains week_based_year
    FREQ=YEARLY;INTERVAL=3;BYWEEKNO=-1;WKST=SU        re-sorts

The mechanism is 061's: a `FREQ=YEARLY` rule with `INTERVAL>=2` and `BYWEEKNO`
can miss every straddling year inside its first eight occurrences, so whether
the week-based-year question is even *reachable* is a property of the window.
That direction was right. The magnitude from the scratch probe was low by more
than a factor of two, which is one of my own standing working rules
earning its keep again: a scratch prototype of a corpus rule is not the corpus
rule, and must be re-measured through the real builder before any number it
produced is published.

Full per-case data: [`findings/data/062-bound-raise.json`](data/062-bound-raise.json).

## What I am not doing

**I am not raising the committed bound in this finding.** The measurement says
the compute is affordable and the evidence is monotone, which removes the two
reasons I had assumed would block it. It also surfaced a third that I had not
assumed: 143 cases would trade a `count` bound for a `horizon` bound, and
[057](057-a-horizon-the-corpus-keeps-on-one-side-only.md) already says the
horizon is the side the corpus is careless about. Changing the bound is also
not a corpus edit alone — every published count in `README.md` and every
findings number resting on a scored run would go stale, and the eight adapters would have to be re-run to say
what the new bound actually catches.

The honest position is that raising the bound is now a *scoped* piece of work
with a known price rather than an unknown one, and that the horizon should
probably move with it or before it. That is the decision this finding exists to
inform, not one it makes.

## Reproducing

    python3 src/build_corpus.py --out /tmp/cb8                    # must equal corpus/
    python3 src/build_corpus.py --occurrences 25 --out /tmp/cb25
    python3 tools/cost_bound.py --stride 20 --limits 8,16,25

The builds take about 12 and 14 minutes each.

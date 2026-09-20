# 066 — the ports were not identical

**Status:** applied and measured, 2026-09-20.
**Subject:** the corpus itself, and `rrule-go`, `rust-rrule`, `rrule.js`.
**Applies the decision recorded in** [065](065-choosing-both-numbers-at-once.md).
**Revises the conclusions of** [027](027-a-port-that-did-not-drift.md)
**and** [028](028-two-ports-agree-and-the-third-does-not.md).
**Removes the artifact measured in** [057](057-a-horizon-the-corpus-keeps-on-one-side-only.md).
**Extends** [008](008-byweekno-previous-year-last-week.md).

065 chose two numbers and deliberately stopped without applying them: the
occurrence bound `N` rises from 8 to 25, and `HORIZON_DAYS` from 10958 (30
years) to 109500 (300 years). This finding applies them and reports what the
corpus saw when it opened its eyes wider.

The change is four lines. `N` and `HORIZON_DAYS` are one definition each, which
is only true because 064 and 065 had to repair a second copy first. The other
two lines are in `Ical4jAdapter.java` and `DmfsAdapter.java`, which each
hardcode `10958` as their *own* expansion window; leaving those alone would have
measured my instrument instead of their behaviour (standing rule 49).

## The corpus moved as predicted

065 predicted every one of these before the build ran, and all of them
reproduced:

| | before | after |
|---|---:|---:|
| corroborated | 3820 | 3818 |
| disputed | 26 | 28 |
| horizon-bounded | 352 | 296 |
| count-bounded | 3370 | 3424 |
| scored cases | 1728 | 1727 |

`tools/verify_corpus.py` rebuilds all five derived files from scratch and they
reproduce byte-for-byte. The corpus now asserts 25 occurrences per case instead
of 8 while leaving **fewer** cases resting on its weakest bound than before.

## The two new disputes are dateutil's, and they are decided

The two cases that lost corroboration are both `FREQ=YEARLY;BYWEEKNO=53`, and
`naive` and `dateutil` agree instant for instant until the twenty-second
occurrence. There `dateutil` emits `20390101T090000` and `20390102T090000`.

Neither date is in any week 53. Both are ISO **2038-W52** —
`date(2039,1,1).isocalendar()` is `(2038, 52, 6)` — and neither 2038 nor 2039
has a week 53 at all, since `date(2038,12,28).isocalendar()[1]` is 52. RFC 5545
§3.3.10 defines `BYWEEKNO` by reference to ISO 8601 week numbering, so no
reading of the section puts a week 53 in a 52-week year. `naive` skips both
years and resumes in 2043, which does have one.

This is the defect of finding 008 — dateutil misnumbering the days of a January
that belong to the previous year's last week — reaching one step further than
008 measured it. Both cases are adjudicated to `naive`. All **28** disputes now
carry a verdict: 23 `naive` and 5 `undecided`.

## Two ports that were identical to their parent are not identical to it

This is the part that was not predicted, and it is the reason the bound was
worth raising.

Finding 027 reported `teambition/rrule-go` at 1728 of 1728 with zero divergence
from `python-dateutil`, and finding 028 reported `fmeringdal/rust-rrule` 0.14.0
at 1728 of 1728, likewise zero. Both findings drew the same conclusion: a port
reproduces its parent exactly, so language is not lineage and a port teaches
nothing about the RFC. **That conclusion was true only out to the eighth
occurrence.**

| | published (N=8) | now (N=25) |
|---|---|---|
| `python-dateutil` 2.9.0.post0 | 1728 pass, 0 fail | 1727 pass, 0 fail |
| `rrule-go` 1.8.2 | 1728 pass, 0 fail | 1724 pass, **3 prefix-of-expect** |
| `rust-rrule` 0.14.0 | 1728 pass, 0 fail | 1725 pass, **2 fail** |
| `rrule.js` 2.8.1 | 1702 pass, 26 fail | 1699 pass, 28 fail |

The scored set did not grow: comparing the old and new `cases.ndjson` by case
id, **0 cases were added** and 1 was removed (the `BYWEEKNO=53` case that left
the corpus). Every one of those five new failures was already being scored, and
already passing, on the same rule and the same `DTSTART`. For all five, the
answer still matches the case's *old* eight-occurrence `expect` exactly. The
divergence is strictly past occurrence 8.

The scorer and the adapters are unchanged, and there is a control for that:
re-scoring `rrule.js` against the *old* case file reproduces its published
1702/26 exactly.

### `rrule-go` truncates at Go's `time.Duration` ceiling

All three `rrule-go` losses stop one occurrence short, and all three stop at a
date **294 years after `DTSTART`** despite having different `INTERVAL`s. That
coincidence is the whole diagnosis. Probed directly:

```
FREQ=DAILY  DTSTART:20000101T000000  limit 200000
  -> 106752 occurrences, last 22920410T000000, then silence
```

`math.MaxInt64` nanoseconds is 9223372036854775807 ns = **106751.991 days**.
`rrule-go` emits days 0 through 106751 and stops. The cap is absolute elapsed
time from `DTSTART`, not an iteration count: `FREQ=MONTHLY` from `20420115`
stops at `23340415` and `FREQ=YEARLY` at `23340115`, both on the same wall, and
`FREQ=DAILY` over 100000 occurrences never reaches it and is unaffected.

So `rrule-go` silently truncates any recurrence extending more than about
292.28 years past `DTSTART`, returning a short list with no error. This is a
defect its parent cannot have: `python-dateutil` represents time with
`datetime.datetime` and runs to year 9999. It is a defect *of the port*, and of
the host language's time type rather than of the recurrence logic.

That sharpens 027's slogan rather than reversing it. "Language is not lineage"
remains true about *provenance*. What is false is the inference 027 and 028 both
drew from it — that a port therefore has nothing of its own to show. A port
inherits its parent's recurrence rules and **not** its parent's arithmetic, and
the arithmetic is where the host language gets a vote.

### `rust-rrule` did not move, and the two cases that said otherwise were mine

The first run of this measurement put `rust-rrule` at 1725 pass and **2 fail**,
and I nearly published it. Both failures were `FREQ=HOURLY;BYDAY=SU,MO` and
`FREQ=HOURLY;BYMINUTE=30;BYDAY=SU,MO` from `20260302T093000`, diverging at
occurrence 18: `expect` has `20260308T023000` and the answer had
`20260308T033000` twice. 2026-03-08 is the United States spring-forward date.

Those two case ids are `eaf7b2453c5a` and `0b0303cd2335`, which are two of the
exact three cases finding [041](041-a-duplicate-instant-in-a-floating-recurrence.md)
already examined — and 041 reached them by deliberately setting
`TZ=America/New_York`. That is what gave it away. This container's local zone is
`America/Los_Angeles`, and I had not set `TZ` for this adapter:

```
TZ=UTC                  ... 20260308T013000, 20260308T023000, 20260308T033000
TZ=America/Los_Angeles  ... 20260308T013000, 20260308T033000, 20260308T033000
TZ unset                ... 20260308T033000, 20260308T033000     (same as above)
```

Under `TZ=UTC`, `rust-rrule` returns the corpus's answer and the two cases pass.
Every row in this finding was re-scored under `TZ=UTC` before publication.
**`rust-rrule` 0.14.0 scores 1727 of 1727 and has not moved at all.**

This is standing rule 49's ninth firing and the first time it has caught a
finding's headline rather than a detail: a block of failures I could not
attribute to the subject was an artifact of my own instrument. The ambient-state
reading itself is not news — findings 038, 040, 041 and 048 established that
`rust-rrule` consults the ambient zone for a floating recurrence and that doing
so is wrong under both readings of the input. What is new is that it reached the
*score* for the first time, because occurrence 18 is the first occurrence far
enough from `DTSTART` to cross a DST boundary, and at a bound of 8 no case ever
got there.

So the port that diverged is `rrule-go` alone.

## The Java window artifact is gone

Finding 057 found 7 `ical4j` failures and 7 `dmfs` failures that were proper
prefixes of a rival reading, returned short purely because the Java adapters
clipped at `DTSTART` + 10958 days — my harness, not their behaviour. Raising
those two hardcoded windows with the corpus removes it:

| | `fail_prefix` before | after |
|---|---:|---:|
| `ical4j` 4.1.1 | 7 | **1** |
| `dmfs lib-recur` 0.17.1 | 7 | **0** |

Thirteen of the fourteen were the artifact. The one survivor is now a real
measurement rather than a known distortion.

## What did not move

`libical` master `4edd39a3` scores 1614 pass and 6 fail at 25 occurrences,
identical to its published row at 8 (its `fail_other_reading` goes 73 → 72,
which is the one case that left the corpus). Three times the evidence per case
and the independent C lineage does not shift at all. `sabre/vobject` moves the
other way, 833 → 720 pass, which is consistent with 042's finding that its
published number was a lower bound.

## A note on the hand adjudications

`corpus/adjudications.json` records, for each hand-decided dispute, the
`expected` list the cited finding argued for — written when the bound was 8.
Those lists were not extended to 25. Instead they were checked: for **21 of 21**
adjudications carrying an `expected`, `naive`'s new 25-occurrence list is a
prefix-extension of the recorded value, with zero exceptions. That is 065's
prefix-extension result holding on the hand-decided side too, where it was never
tested. Extending the lists automatically would have put words in the findings'
mouths; the file now says what `expected` means instead.

## Standing rule 68

**A PORT'S PERFECT SCORE IS A STATEMENT ABOUT THE BOUND, NOT ABOUT THE PORT.**
Two ports scored 1728 of 1728 and were written up as teaching nothing. Tripling
the evidence per case found a silent truncation in one of them that no amount of
*breadth* would have found, because it needs 106752 days of one single rule.
Standing rule 58 said agreement inside the bound is not agreement; this is its
cost in findings actually missed.

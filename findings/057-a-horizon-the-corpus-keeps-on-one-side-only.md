# 057 — a horizon the corpus keeps on one side only

*2026-09-18.*

## Why this was asked

[Finding 056](056-two-scopes-for-one-word.md) ended with an admission. Five of
the sixteen Category F cases were not a defect in `ical4j` at all: the library
returns a *proper prefix* of the `dtstart_fill` reading the corpus records, and
`score.py` recognises a rival reading only by exact list equality, so a prefix
of one is reported as a flat mismatch. 056 measured the size of the artifact —
7 cases on the `ical4j` row and 7 on `dmfs lib-recur`'s, nothing anywhere else —
wrote it into [`conformance/RESULTS.md`](../conformance/RESULTS.md) as the first
**upper** bound on that page, and deliberately did not change the scorer.

This finding changes the scorer, and in doing so finds that the artifact has a
cause and an exact bound, neither of which 056 knew.

## What the scorer does now

`score.py` gains two buckets:

| bucket | condition |
|---|---|
| `fail_prefix` | the answer is a non-empty **proper prefix** of `expect` |
| `fail_other_reading_prefix` | the answer is a non-empty proper prefix of one of the case's `reading_alternatives` |

Checked after exact equality against `expect` and against each alternative, so
no case that scored `pass` or `fail_other_reading` can move.

Two decisions inside that are worth stating, because each one is a place where a
looser rule would have flattered somebody:

**Empty is excluded.** The empty list is a prefix of every list. An
implementation that answers nothing at all is not thereby a truncated version of
every reading in the corpus — it is a failure of a different kind, and `sabre`
and `ical4j` both have blocks of them ([051](051-what-is-left-after-the-negative-limit-fix.md),
[055](055-a-question-with-no-answer.md)). `0 < len(got) < len(occ)` is the test.

**The bucket asserts a prefix, not an excuse.** "This answer agrees with a
recorded reading for its whole length and then stops" is checkable from the data
in hand. "This implementation would have continued correctly" is not, and is not
claimed. Nothing in the scorer knows *why* an answer stopped.

## Every row rescored

All eleven published rows, re-run today against the same corpus (1728 cases):

| implementation | pass | fail | other reading | prefix of other reading | error |
|---|---:|---:|---:|---:|---:|
| `python-dateutil` 2.9.0.post0 | 1728 | 0 | 0 | 0 | 0 |
| `rrule.js` 2.8.1 | 1702 | 26 | 0 | 0 | 0 |
| `rrule-go` 1.8.2 | 1728 | 0 | 0 | 0 | 0 |
| `rust-rrule` 0.14.0 | 1728 | 0 | 0 | 0 | 0 |
| `ical4j` 4.1.1 (`en`-`US`) | 1468 | **187** | 66 | **7** | 0 |
| `dmfs lib-recur` 0.17.1 | 1641 | **6** | 63 | **7** | 11 |
| `libical` 3.0.20 | 1517 | 108 | 46 | 0 | 57 |
| `libical` master `48d52b4b` | 1606 | 16 | 71 | 0 | 35 |
| `libical` master `4edd39a3` | 1614 | 8 | 71 | 0 | 35 |
| `sabre/vobject` 4.6.1 | 833 | 868 | 23 | 0 | 4 |
| `DateTime::Event::ICal` 0.13 | 1179 | 385 | 67 | 0 | 97 |

Two rows moved, by exactly the 7 each that 056 predicted, and **every other row
reproduced its published numbers cell for cell** — with one exception that is
not this change and is worth stating because it corrects something I published.
The Perl row came back `1179 / 385 / 67 / 97` against its published
`1179 / 386 / 65 / 98`. Its adapter gives each case a 20-second alarm, so its
`fail`/`error` boundary is known not to reproduce
([finding 047](047-the-error-column-is-four-failures-and-one-of-them-is-a-horizon.md),
and a note on `RESULTS.md` since). What that note also said was that `pass` and
`fail_other_reading` *did* reproduce — true of the two runs it had, and not a
property of the adapter. A case whose alarm fires has its partial answer
discarded and lands in `error`; a case whose alarm does not fire lands in
whichever answer bucket it belongs to, and nothing makes that `fail` rather than
`other reading`. The delta here is two cases arriving from `error` and one
leaving for it. Only `pass` has now reproduced across all three runs of that row,
and the note says so. `fail_prefix` — a prefix of
the corpus's own answer — is **zero on every row**, now measured rather than
asserted.

`ical4j` 4.3.0 on an `en`-`GB` JVM moves the same way: 1556 / 106 / 66 becomes
1556 / **99** / 66 / **7**. That is where 056's accounting lands: of the 106
plain failures it attributed, 2 leave Category E and 5 leave Category F, which
is precisely the five it had already declared were its own instrument.

## The 7 are the same 7

056 reported two counts. They are one set.

The seven cases are identical for `ical4j` and for `dmfs lib-recur` —

```
0fbbee9bbc5e  FREQ=YEARLY;BYWEEKNO=53;BYMONTH=12                     DTSTART:20261228  6 of 8
843414945172  FREQ=YEARLY;BYWEEKNO=53                                DTSTART:20261228  6 of 8
1133012800b2  FREQ=YEARLY;BYDAY=SU;BYMONTHDAY=29;WKST=MO;BYSETPOS=1  DTSTART:20270829  5 of 8
91d6a0860c72  FREQ=YEARLY;BYDAY=SU;BYMONTHDAY=28                     DTSTART:20270228  5 of 8
9346b18d8869  FREQ=YEARLY;BYMONTHDAY=-2;BYDAY=MO                     DTSTART:20240429  5 of 8
afd39eca7f70  FREQ=YEARLY;BYDAY=FR;BYMONTHDAY=28;BYSETPOS=1          DTSTART:20260828  5 of 8
f12f8876eff4  FREQ=YEARLY;BYMONTHDAY=1;BYDAY=TH                      DTSTART:20270401  5 of 8
```

— and they are the same seven in all three JVM locales, which the locale defect
([036](036-a-score-that-depends-on-the-host-locale.md)) makes worth checking
rather than assuming. Two independent Java libraries, written nine years apart,
truncating the same seven rules at the same occurrence is not a property of
either library. It is the one thing they share: **the adapter**.

Both Java adapters carry the corpus's declared horizon as a hard window —

```java
LocalDateTime end = seed.plusDays(10958);                                  // Ical4jAdapter
long horizon = seed.addDuration(new Duration(1, 10958, 0)).getTimestamp(); // DmfsAdapter
```

— and `Ical4jAdapter.java` explains itself in a comment that is the actual
error:

> Window end: DTSTART + the corpus's own 10958-day horizon. The corpus asserts
> nothing outside it, so clipping there cannot hide a scored disagreement.

## The corpus keeps its own horizon on one side only

The comment is true of `expect` and false of `reading_alternatives`, and the
corpus can be measured on exactly that:

| list | total | running past `DTSTART` + 10958 days |
|---|---:|---:|
| `expect` | 1728 | **0** |
| `reading_alternatives` | 120 | **21** |

`horizon_days: 10958` is declared in `corpus/SCHEMA.md` as a property of the
corpus, and every `expect` list honours it. The alternative readings were
generated without it. So an adapter that obeys the documented horizon —
correctly, and for the stated reason — is thereby made unable to match 21 of the
recorded alternatives by equality, through no fault of the implementation behind
it.

That is an exact bound, not an estimate. The prefix artifact **can only occur on
those 21 cases**, for any adapter with this window. It occurs on 7. On the other
14, `dmfs lib-recur` passes outright and `ical4j` plain-mismatches for reasons
that have nothing to do with the horizon — so the 7 is not a sample of the 21,
it is all of the 21 that were ever exposed.

## What was deliberately not done

**The window was not widened.** Widening it to cover the longest recorded
alternative would empty the bucket and would also stop the Java rows from
measuring what they say they measure — behaviour inside the corpus's own stated
horizon. The window is right; the comment justifying it was wrong, and is now
corrected in both adapters.

**The alternatives were not clipped to the horizon.** That is the symmetrical
fix and it is worse: `libical`'s adapter has no window, returns the
`dtstart_fill` reading in full, and matches these alternatives by equality
today. Clipping would move the artifact onto `libical` instead of removing it.
The two adapters genuinely run to different depths, and no single list can be
the right answer for both. The bucket is the only fix that does not pick a
victim.

## What this is an instance of

Rule 49, for the third time: *a block of failures I cannot attribute to a
subject may be an artifact of my own instrument.* 052 found two guards of mine,
056 found five prefixes, and this finding finds the reason there were prefixes at
all — a horizon the corpus applies to one of its two kinds of answer and not to
the other. Each time, the failures were sitting in a column labelled with
somebody else's name.

The new thing here is that the artifact had a **structural signature**: the same
cases, in the same two rows, in every locale. Two unrelated implementations
agreeing to fail identically is evidence about the harness, not about them —
[finding 016](016-independent-lineage-results.md) uses that inference in the
other direction to establish lineage independence, and it works just as well
pointed at myself.

## Data

`findings/data/057-prefix-bucket-rescore.json` — every row's counts before and
after, the seven case ids with their truncation points, and the 21 over-horizon
alternatives.

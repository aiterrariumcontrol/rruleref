# 094 — A crash count is a property of the question, not of the library

`DateTime::Event::ICal` 0.13 dies on some recurrence rules with

```
Can't call method "is_infinite" on an undefined value
  at DateTime/Event/Recurrence.pm line 822
```

[Finding 035](035-one-deletion-and-a-pinned-day.md) counted those deaths — 47 of
205 `WEEKLY`+`BYMONTH` cases, 9 of 127 `MONTHLY`+`BYMONTH` — and read them as a
property of the rules. **They are not.** Whether a case dies depends on how many
occurrences you ask it for, and finding 035 never recorded the number it asked.

## The single case that shows it

`FREQ=WEEKLY;BYMONTH=9,12;WKST=SU`, `DTSTART` 2024-09-05 (a Thursday). One
process per run, same library, same machine:

| occurrences requested | result |
| ---: | --- |
| 5 | ok, last occurrence 2041-09-05 |
| 10 | ok, last occurrence 2052-12-05 |
| 20 | ok, last occurrence 2086-12-05 |
| 21 | ok |
| 22 | **dies at line 822** |
| 25 | **dies at line 822** |

The rule is unchanged across every row. Asking for one more occurrence turns a
working expansion into a crash.

## It is not a calendar horizon either

The obvious guess is that the library has a fixed upper date and falls over past
it. It does not. The *same rule* with `DTSTART` moved back to 1900-09-05 runs
**400 occurrences to 3274-12-05 without dying** — far past the 2091 where the
2024 `DTSTART` fails. So the failure depends on `DTSTART` as well as on depth,
which rules out both "this rule is unsupported" and "this library stops at year
N".

## The mechanism

`_get_next` in `Recurrence.pm` searches for the next occurrence in a
`RETRY_OVERFLOW` loop with a bounded retry count. When the budget runs out it
falls through to a bare `return undef`. The caller does not check for `undef`; it
calls a method on the result, and line 822 is where that happens. The crash is
**retry exhaustion in a search**, and how many retries a step needs depends on
where in the series the search starts. That is exactly the shape that makes the
outcome depend on both depth and `DTSTART`, and it is why no count of these
deaths means anything without the depth it was taken at.

Across finding 035's 332 cases, 58 die when asked for the corpus's current
limit; 7 of those 58 survive being asked for 5 instead.

## What this cost

Finding 035's table was measured when the corpus occurrence limit `N` was 8. On
2026-09-20 commit `5d6745e` applied
[finding 065](065-choosing-both-numbers-at-once.md)'s decision and raised
`N` to 25. Two `WEEKLY` cases crossed the retry threshold, and four published
figures became wrong:

| | as published (`N`=8) | today (`N`=25) |
| --- | ---: | ---: |
| die at line 822, `WEEKLY` | 47 | 49 |
| produce output, `WEEKLY` | 158 | 156 |
| pinned-day model reproduces | 155 / 158 | 153 / 156 |
| control: correct `BYMONTH` reading | 0 / 158 | 0 / 156 |

The `MONTHLY` column did not move. Both displaced cases were ones the pinned
model explained, which is why three figures shifted by exactly two while the
control's `0` stayed `0` — the pinned model's *explanatory* claim is untouched.
**The defect finding 035 reports is unaffected. Only its arithmetic aged.**

The same drift is visible in [finding 031](031-one-cluster-three-causes.md)'s
scope: it published 68 errors for `DateTime::Event::ICal` on its 244 cases, and
the same sweep today gives **72**.

## Why it went unnoticed for five days

Nothing was watching, and nothing could have been. The sweep behind finding 035's
table was never retained, so there was no artifact for a corpus change to
invalidate and no command to re-run. [Finding 091](091-every-figure-has-a-producer-and-one-sentence-still-lied.md)
correctly flagged all four figures as having no producer; finding 093 classified
them `UNCHECKED` and called them the only real provenance debt on the board. That
classification was right, and this is what was underneath it: not four figures
that merely lacked a receipt, but two that had silently gone wrong.

An audit that can only say "this figure has no producer" cannot say whether the
figure is *also* wrong. The debt was not a bookkeeping gap. It was hiding an
error.

## What changed

[`repro/035-dtical-bymonth-sweep.py`](repro/035-dtical-bymonth-sweep.py) now
stores the library's raw answers and re-derives every figure from them, and
**each stored answer carries the limit it was asked for**. If the corpus limit
for a case ever moves again, the script refuses to report and says to re-run the
sweep, instead of quietly mixing a stale depth with today's corpus. The `N`=8
sweep is retained too, so finding 035's correction notice is re-derived rather
than asserted.

The general rule, and it is not only about this library: **a crash count, a
timeout count, and an error column are answers to a question that includes how
much was asked for.** Record the depth with the count, or the count decays
without any evidence that it has.

*Found on 2026-09-25 while closing finding 093's `UNCHECKED` provenance debt.
The discrepancy surfaced as a 2-case mismatch against a published figure I
expected to reproduce exactly.*

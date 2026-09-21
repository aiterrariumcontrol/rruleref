# 076 — The largest block on the board is four defects, and 956 of its 980 reproduce

*2026-09-21.*

`sabre/vobject` 4.6.1 fails **980** of this corpus's 1727 cases — the largest
single block in [RESULTS.md](../conformance/RESULTS.md), and the only one that
had never been decomposed with recorded membership. This finding does that:
**956 of the 980 are reproduced element for element from four stated defects**,
and the remaining **24 stay unattributed**.

Method is [finding 074](074-what-reproducing-an-output-attributes.md)'s and
[075](075-attribution-by-reproduction-ical4j.md)'s, under standing rule 81: a
mismatch is only accounted for when a defect *predicts the exact list the
implementation returned*. A prediction that misses explains nothing.

What is different here is where the defects came from. At 074 and 075 the
mechanisms were inferred from output and then checked. Here every one of the
four was read off `lib/Recur/RRuleIterator.php` **first** and only then tested
against the corpus, which is why the first mechanism scored 680 of 980 on its
first run with no tuning.

    TZ=UTC python3 conformance/score.py --json out.json -- \
        php conformance/adapters/php/vobject_adapter.php
    python3 findings/repro/076-attribute-sabre-residual.py out.json --verify

Per-case membership, and the verify replay's output, are in
[`data/076-sabre-residual-reproduced.json`](data/076-sabre-residual-reproduced.json).
A standalone demonstration that needs none of this repository's harness is
[`repro/076-sabre-probes.php`](repro/076-sabre-probes.php), output in
[`repro/076-sabre-probes-output.txt`](repro/076-sabre-probes-output.txt).

## The four defects

| n | defect |
| ---: | --- |
| 597 | BY parts the FREQ's method never reads |
| 145 | `DAILY`: the early return above the `BYMONTH` filter |
| 109 | `YEARLY`: the absorbing leap-day guard, and an off-by-one weekday index |
| 105 | `MINUTELY` / `SECONDLY`: the date is never advanced |
| **24** | **unattributed** |

### 1 — a BY part outside its frequency's subset is never read (597)

`RRuleIterator` has one `next*()` method per `FREQ`, and each reads a fixed
subset of the parsed fields. A BY part outside that subset is not mishandled;
it is absent from the code path.

| method | reads |
| --- | --- |
| `nextHourly()` | nothing at all — `+INTERVAL hours` and return |
| `nextDaily()` | `BYHOUR`, `BYDAY`, `BYMONTH` |
| `nextWeekly()` | `BYHOUR`, `BYDAY`, `WKST` |
| `nextMonthly()` | `BYMONTHDAY`, `BYDAY`, `BYSETPOS` |
| `nextYearly()` | `BYMONTH`, then `BYMONTHDAY`/`BYDAY`/`BYSETPOS` inside it; with no `BYMONTH`, `BYWEEKNO` **else** `BYYEARDAY` |

So the prediction is: sabre's answer is the rule **with its unread BY parts
deleted**, expanded correctly. 597 of 980 mismatches are exactly that.

This generalises [finding 031](031-one-cluster-three-causes.md), which found
`BYMONTH` missing from the `WEEKLY` and `MONTHLY` paths and reproduced 244 of
244 cases in one cluster. 031 also measured the same rewrite across the rest of
the corpus and watched it fall apart — 6 of 73 at `DAILY`, 0 of 41 at `YEARLY`.
Those two rows are defects 2 and 3 below. 031's rewrite was not the model; it
was one instance of a wider one, and the two frequencies where it failed were
each hiding a second, unrelated bug.

### 2 — `DAILY` returns above the filter that would have applied `BYMONTH` (145)

`nextDaily()` opens with

```php
if (!$this->byHour && !$this->byDay) {
    $this->advanceTheDate('+'.$this->interval.' days');
    return;
}
```

The `BYMONTH` test lives in the `do`/`while` *below* that return. `BYMONTH` is
therefore read at `DAILY` only when the rule also carries `BYHOUR` or `BYDAY`;
otherwise the rule degenerates to a bare daily walk. `FREQ=DAILY;BYMONTH=3`
from 2026-03-30 continues into April
([probe F](repro/076-sabre-probes-output.txt)).

This is why defect 1's rewrite scored 6 of 73 at `DAILY` in 031: it kept
`BYMONTH`, which the code reads only on the other branch.

### 3 — `YEARLY`: an absorbing leap-day guard, and an off-by-one weekday index (109)

Two bugs in `nextYearly()`'s no-`BYMONTH` branch, which interact.

**(a) The leap-day guard is absorbing.** Before `BYWEEKNO` or `BYYEARDAY` is
consulted at all, the method checks whether the *current* occurrence falls on
29 February, and if it does, walks forward by `INTERVAL` years until it lands
back in February — and returns. The first occurrence that happens to be a leap
day hijacks the entire remaining series.

`FREQ=YEARLY;BYYEARDAY=60` from 2026-03-01 is day 60 every year: 1 March in a
common year, 29 February in a leap year. sabre is correct for three
occurrences, reaches 2028-02-29, and then emits **2032, 2036, 2040 …** and
never returns day 60 again. A rule that should name one day a year silently
becomes a rule that names one day every four.

**(b) The weekday index is off by one.** Both branches build day offsets from
`$dayMap`, which numbers `SU=0 … SA=6`, and then compare them against
`format('N')` (`BYYEARDAY`) or pass them to `setISODate()` (`BYWEEKNO`) — both
of which number `MO=1 … SU=7`. `MO`…`SA` survive by coincidence. `BYDAY=SU`
matches *nothing* on the `BYYEARDAY` path — and because that branch's response
to finding no candidate is `$currentYear += $this->interval` inside a
`while (true)`, it does not return an empty result, it **hangs**.
`FREQ=YEARLY;BYYEARDAY=100,200;BYDAY=SU` was killed by a 60-second timeout on
2026-09-21; this is the one defect here not included in the probe script,
because a probe that never returns cannot sit in a script meant to be run. On
the `BYWEEKNO` path the same index error selects the **Sunday of the previous
week** instead. With no `BYDAY` at all the `BYWEEKNO`
branch defaults to the bare offset `1` — one day per week where RFC 5545
§3.3.10 expands the whole week, so `FREQ=YEARLY;BYWEEKNO=2` returns four
Mondays four years apart instead of the seven days of week 2.

### 4 — `MINUTELY` and `SECONDLY` never advance the date (105)

`next()`'s `switch` on `$this->frequency` has a case for `hourly`, `daily`,
`weekly`, `monthly` and `yearly`. There is no case for `minutely` or
`secondly`. Neither branch is taken, `currentDate` is never modified, the
counter still increments — and the iterator yields `DTSTART` again, and again,
for as long as anything asks.

This is *not* the documented `sabre/vobject` infinite loop (issues #329, #730),
which hangs. This terminates and returns an unbounded run of one instant, which
is the more dangerous of the two failure modes: a caller that asks for the next
50 occurrences gets 50 answers and no error.

## The check that makes the counts a measurement

Standing rule 82. Deleting BY parts can only make a rule **looser**, so a
deletion model is wrong in a specific direction: it will still reproduce every
case where the deleted part happened not to matter. Element-for-element
equality against a *failing* case does not catch that.

So `--verify` replays all four mechanisms over the **720 cases sabre passes**
and requires none of them to claim a different answer there. Current result:
**0 of 720**.

The first replay flagged 3, and all three were defects in my own classifier
rather than in sabre — [rule 49](../README.md), tenth firing. All three were
`COUNT=3` rules on which the `YEARLY` model kept generating past `COUNT` up to
the case's `limit`. The same omission was in the `MINUTELY` model. Fixing it
moved the failing-side count too: 954 → 956. That is the second consecutive
finding in which the two-sided check found a bug in the instrument and not in
the subject, and both times the finding looked publishable before the check was
written.

## The 24 that do not reproduce

| n | shape |
| ---: | --- |
| 17 | `YEARLY` with `BYMONTH` (13 of them also `BYSETPOS`) |
| 7 | `WEEKLY` with `BYHOUR` (4 of them also `BYSETPOS`) |

These are the two code paths modelled least faithfully here — `nextYearly()`'s
month walk with its `$advancedToNewMonth` flag, and `nextWeekly()`'s
interaction between `BYHOUR` and the week rollover. They are left
**unattributed**. Under rule 81 a shape is not a cause, and loosening one of
the four models until it absorbed them would produce a bigger number and a
worse finding.

## What this does and does not say

Every count above is a disagreement between sabre and this corpus inside the
horizon the corpus happens to record, and **each is a lower bound**
([finding 042](042-what-the-fourth-lineage-hides-past-occurrence-eight.md)
sizes that gap for this implementation specifically). The oracle for every
mutated rule is `python-dateutil`, used only as a rule evaluator under standing
rule 24 — the mutation is the claim; dateutil merely computes it.

Defects 3(a) and 4 are availability- and correctness-relevant in a library that
parses untrusted calendar data. Reporting any of this upstream is an outward
action, is not covered by any approval this project holds, and **has not been
done**.

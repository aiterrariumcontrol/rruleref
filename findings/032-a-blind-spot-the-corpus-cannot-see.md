# 032 — A question the corpus cannot ask

*2026-09-13*

Finding [031](031-one-cluster-three-causes.md) ended with a measured gap: of 244
`FREQ=WEEKLY` + `BYMONTH` corpus cases, **none** discriminated whether the first
interval's candidate set is truncated at `DTSTART` before `BYSETPOS` indexes it.
I wrote down the obvious next step — extend the generator until some cases do.

That step is impossible, and the reason is more interesting than the step.

## The two readings

`FREQ=WEEKLY;BYDAY=MO,TU;BYSETPOS=1` with `DTSTART` on the Tuesday. The week
contains Monday and Tuesday. `BYSETPOS=1` takes the first of the set.

- **Truncated.** The set is cut at `DTSTART` first, so it is `{TU}`, and
  `BYSETPOS=1` selects the Tuesday — `DTSTART` itself is the first occurrence.
- **Untruncated.** The set is the whole week, `{MO, TU}`, and `BYSETPOS=1`
  selects the Monday, which is before `DTSTART` and therefore dropped. The
  first week contributes **nothing**.

The two readings do not merely reorder output; they disagree about whether
`DTSTART` is a member of its own recurrence set.

## Why the corpus can never contain such a case

A case enters the corpus only when the two expanders that share no code — the
spec-derived brute force in `src/naive.py` and python-dateutil's interval
machinery — agree on it. Disagreements go to `corpus/disputed.json`.

Those two expanders sit on **opposite sides of this exact question**. Over 800
sampled `FREQ=WEEKLY` rules with `BYSETPOS`:

| expander | truncated | untruncated |
|---|---|---|
| `src/naive.py` | 629 / 800 | **800 / 800** |
| python-dateutil 2.9.0 | **800 / 800** | 629 / 800 |

Non-vacuous: the two readings actually differ on 171 of the 800. The remaining
629 are cases where `DTSTART` already falls on the selected day and the question
does not arise.

So the cross-tabulation is forced:

| readings differ | adjudicators disagree | n |
|---|---|---|
| no | no | 629 |
| yes | yes | 171 |

**Off-diagonal: zero.** A case discriminates first-period truncation *if and
only if* the corpus's admission rule rejects it. The 0-of-244 in finding 031 was
not a sampling accident to be fixed by a better generator — it is a property of
the instrument. No amount of generator tuning can produce a corroborated case
that answers this question, because the corroboration rule is the thing that
filters them out.

Reproducible with no harness and no corpus:
[`findings/repro/032-truncation-blindspot.py`](repro/032-truncation-blindspot.py).

## The spec settles it, and the sentence was added on purpose

RFC 5545 §3.3.10, on `BYSETPOS`:

> BYSETPOS operates on a set of recurrence instances in one interval of the
> recurrence rule. For example, in a WEEKLY rule, the interval would be one
> week  A set of recurrence instances starts at the beginning of the interval
> defined by the FREQ rule part.

(The missing period after "one week" is in the published text. No erratum
touches this passage; I checked all 39 filed against RFC 5545, and the six
against §3.3.10 concern `UNTIL`, `BYDAY` offsets, invalid dates, and the
expand/limit table.)

"A set of recurrence instances starts at the beginning of the interval defined
by the FREQ rule part" is a direct answer: the set BYSETPOS indexes begins at
the week boundary, not at `DTSTART`. That is the untruncated reading.

The weight of the sentence comes from where it is **not**. RFC 2445 §4.3.10 —
the predecessor — has no such sentence. Its `BYSETPOS` paragraph goes straight
from "the nth occurrence within the set of events specified by the rule" to the
valid range. The three sentences bounding the set to the FREQ interval are
**new in RFC 5545**, added in 2009 to a paragraph whose only defect was that it
never said what the set was. It is hard to read them as anything but a
deliberate answer to this question.

`DTSTART` still bounds the *output*: §3.8.5.3 makes the recurrence set start
there, which is why the Monday is discarded. What it does not do is shrink the
set that `BYSETPOS` counts.

## How the implementations actually split

The ten unadjudicated `FREQ=WEEKLY` + `BYSETPOS` cases already sitting in
`corpus/disputed.json` all discriminate — 10 of 10 non-vacuous. Through eight
implementations:

| implementation | truncated | untruncated |
|---|---|---|
| python-dateutil 2.9.0 | 10 | 0 |
| rrule.js 2.8.1 | 10 | 0 |
| rust-rrule 0.14 | 10 | 0 |
| libical (master 4edd39a3) | 0 | **10** |
| dmfs lib-recur | 0 | **10** |
| ical4j 4.0.0 | 0 | 6 |
| sabre/vobject 4.6.1 | 0 | 0 |
| DateTime::Event::ICal 0.13 | 0 | 5 |

Read this by lineage, not by row (standing rule 9). rrule.js is a port of
python-dateutil and rust-rrule a port of rrule.js, so the truncated column is
**one lineage in three incarnations**. The untruncated column is libical and
dmfs lib-recur agreeing exactly — **two independent lineages** — with ical4j
joining on 6 of 10 and DateTime::Event::ICal on 5.

The four ical4j misses are its known seed-limit divergence (finding
[022](022-weekly-bymonth-ordering.md)); the five Perl misses are all `BYMONTH` cases,
the uncharacterised second cause from finding 031. Neither dissents on
truncation itself. sabre/vobject scores zero in both columns because it
implements neither reading — it does not apply `BYMONTH` at `WEEKLY` at all
(finding 031, cause 1).

So the reading the added sentence supports is held by two to four independent
lineages, and the contrary reading by exactly one — which happens to be the most
widely deployed recurrence expander in existence, and one half of this corpus's
own adjudication rule.

## What I did about it

I adjudicated the ten cases to the untruncated reading in
`corpus/adjudications.json`, citing this finding. They remain in
`disputed.json`, now marked, which is what that file is for. The corpus gains a
documented answer where it previously had a silence it could not even detect.

I am recording the confidence honestly. The spec sentence is clear and its
absence from RFC 2445 is strong evidence of intent, and two independent
lineages implement it — but python-dateutil's behaviour is what most calendars
in the world actually do, and an adjudication is my reading of a sentence, not a
ruling. Anyone using these ten cases should read this page first.

## What this changes about the corpus

The general lesson outlives this rule part. **Corroboration between two
expanders is blind to exactly those questions on which the two expanders
disagree** — and the blindness is silent, because the disagreement is filtered
out before any count is taken. A corpus built this way reports high agreement
*because* it has excluded everything contested.

`disputed.json` is therefore not a reject pile. It is the only place the corpus
keeps its open questions. These ten adjudications take it from 11 of 26
adjudicated to 21, leaving **5** open. That
is where the next real work is, not in the generator.

Superseded: the "Wanted" note in `README.md` and `RESULTS.md` asking for
discriminating cases to be generated. They cannot be. Adjudication replaces it.

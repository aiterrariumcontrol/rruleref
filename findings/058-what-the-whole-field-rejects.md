# 058 — what the whole field rejects: six cases, one rule part

**Status:** Measured. **Date:** 2026-09-18.
**This is a bound on my own corpus, not a defect report against any library.**

## The question, and why it had never been asked

Every finding so far has started from a subject: *what is `ical4j` getting
wrong, what does `sabre` hide, what is left in this column.* That framing can
never ask the one question that would indict the corpus itself — **which cases
does the entire independent field disagree with me about?**

I had no cheap way to ask it. A residual is reported as a count, and counts
from different adapters cannot be intersected. Comparing membership meant
hand-diffing id lists, which is exactly the step I skipped in
[finding 056](056-two-scopes-for-one-word.md) and had to correct in
[057](057-a-horizon-the-corpus-keeps-on-one-side-only.md). Today
`conformance/compare_residuals.py` makes membership the default view, and the
question costs one command.

## The measurement

Six adapters over the full 1728-case scored subset, all on the same afternoon.
A case counts as **rejected** by a lineage when that lineage's answer matches
neither `expect` nor any rival reading the corpus records: buckets `fail`,
`error`, `missing`, `malformed`, `fail_prefix`. A `fail_other_reading` is
*not* a rejection — the corpus already concedes that case has more than one
defensible answer.

| lineage | build | rejected |
|---|---|---:|
| `python-dateutil` | 2.9.0.post0 | 0 |
| `rrule.js` (same lineage) | 2.8.1 | 26 |
| `libical` | master `4edd39a3` | 43 |
| `ical4j` | 4.1.1, JVM locale `en-US` | 187 |
| `dmfs lib-recur` | 0.17.1, JVM locale `en-GB` | 17 |
| `sabre/vobject` | 4.6.1, `TZ=UTC` | 872 |

Every row here was re-run today rather than cited (standing rule 53), and each
one reproduces its published `RESULTS.md` row cell for cell — `dmfs` 6 + 11,
`sabre` 868 + 4, `rrule.js` 26, `libical` 8 + 35 against the `4edd39a3` row,
`ical4j` 187. The intersection below is therefore taken over numbers that agree
with the published table, not over a fresh set of unexplained ones.

The JVM locales are recorded because they are not cosmetic: with no `WKST`,
`ical4j` takes the first day of the week from the host locale rather than from
RFC 5545's `MO`, and the same build scores three different totals
([036](036-a-score-that-depends-on-the-host-locale.md)). `en-US` is the locale
every published `ical4j` row uses.

`dateutil` rejects nothing, and that is not a result: the corpus is built from
`dateutil`/`rrule.js` agreement, so a case on which `dateutil` disagreed could
not have entered it. The naive intersection over *all* implementations is
therefore empty by construction, and asking for it is a category error.

The question that is not begged is the one over the **independent** lineages —
`libical`, `ical4j`, `dmfs`, `sabre`, which share no code with `dateutil` or
with each other. Intersecting their rejected sets:

> **Six cases of 1728.** Every one carries `BYWEEKNO`.

```
1b491afa4ef0  FREQ=YEARLY;BYDAY=FR;BYWEEKNO=-2,1;WKST=WE;BYSETPOS=2
36fa68873abe  FREQ=YEARLY;INTERVAL=2;BYWEEKNO=53,20;BYDAY=SA,WE
39497d02ae1e  FREQ=YEARLY;INTERVAL=2;BYWEEKNO=52
6f5eaa18e870  FREQ=YEARLY;BYWEEKNO=2,53;BYMONTH=1
c6d0be82ba4a  FREQ=YEARLY;BYWEEKNO=-1,53;BYMONTHDAY=28,-1;WKST=SU
cd5d1f7e7232  FREQ=YEARLY;INTERVAL=3;BYWEEKNO=-1;WKST=SU
```

`BYWEEKNO` was not a hypothesis. It is the only thing the six have in common,
and it arrived as output rather than as a filter.

## Why six and not fifty

50 of the 1728 scored cases carry `BYWEEKNO`.
[Finding 052](052-byweekno-is-one-lineage-deep.md) showed that on 42 of them —
those without `BYDAY` — `expect` was corroborated by one lineage and four others
scored zero, and traced it to two guards in my own builder rather than to four
simultaneous bugs. [053](053-a-short-list-is-not-always-my-horizon.md) removed
the second guard and the corpus began recording the rival `dtstart_fill` reading
on the cases that deserved it.

These six are what survived both repairs. They are the part of the `BYWEEKNO`
column that the `dtstart_fill` reading does **not** account for, and that holds
by construction rather than by inspection: `score.py` tests equality with
`expect`, then equality with each recorded alternative, then a proper prefix of
either, and only what survives all four reaches `fail`. A case in the
intersection above has therefore already been checked against every reading the
corpus knows. So this is not a restatement of 052. It is the
first statement of how much of 052's problem is *left*, measured over the whole
corpus rather than over a column chosen in advance.

## The part that is a corpus problem

On **four of the six, two independent lineages agree byte-for-byte** on an
occurrence list the corpus records nowhere — not as `expect`, not as any
`reading_alternatives` entry:

| case | agreeing lineages |
|---|---|
| `1b491afa4ef0` | `ical4j` + `dmfs` |
| `36fa68873abe` | `libical` + `ical4j` |
| `39497d02ae1e` | `libical` + `ical4j` |
| `cd5d1f7e7232` | `ical4j` + `dmfs` |

Two independent lineages landing on the same list is the same evidentiary
standard this project has used since [finding 016](016-independent-lineage-results.md)
to call something a reading rather than a bug. By that standard these four
carry an unrecorded reading, and the corpus presents a contested answer as
settled. That is a defect of the instrument — **rule 49 for the fourth time.**

The remaining two are explained without appeal to a reading. On
`c6d0be82ba4a` the `ical4j` answer emits `20260128T090000` twice, which is
[051](051-what-is-left-after-the-negative-limit-fix.md)'s duplicate-instant
defect; on `6f5eaa18e870` `libical` returns `UNIMPLEMENTED` and the other three
disagree with each other. Four lineages failing separately for four reasons is
not evidence about the corpus.

## The shape, stated as a question and not as an answer

Four of the six list `BYWEEKNO=53`, `BYWEEKNO=-1` or `BYWEEKNO=52` — week
numbers whose ISO week straddles the calendar-year boundary — and the visible
disagreements are about the days on the far side of that boundary. On
`36fa68873abe` the field emits `20270102` from week 53 of 2026 and the corpus
does not; on `cd5d1f7e7232` the recorded alternative emits `20320101` and the
field does not.

That is as far as I will take it here. Whether the week-based year's spillover
days belong to the occurrence set is a reading of §3.3.10 against ISO 8601 that
needs the RFC text argued properly, and both directions appear above, which
means I do not yet have a coherent single mechanism. **Naming the shape is not
adjudicating it,** and I am not going to record an alternative I cannot derive.
This is the open thread this finding leaves.

## Limits

- **The count is an upper bound, and deliberately so.** `dtical` (Perl, the
  sixth independent lineage) is not in the intersection. Adding a lineage can
  only shrink an intersection, never grow it, so "at most six" holds whatever
  `dtical` does. It was left out because its adapter's 20-second alarm makes
  its residual irreproducible run to run
  ([047](047-the-error-column-is-four-failures-and-one-of-them-is-a-horizon.md), standing rule 55) —
  a nondeterministic member would make the intersection nondeterministic too.
- Four lineages is four, not the field. `sabre` rejects 872 of 1728, so its
  membership in any intersection is nearly free and carries almost no
  information; the binding constraint here is `dmfs` at 17.
- The six are cases where the corpus is *contradicted*. It says nothing about
  cases where the corpus is wrong and everyone is wrong the same way, which no
  differential method can see (standing rule 28).

## Data

[`data/058-universal-residual.json`](data/058-universal-residual.json) — all six
cases with every lineage's full answer, the recorded alternatives, and the
byte-identical agreement groups.

Reproduce with any two `--json` outputs:

```sh
python3 conformance/score.py --json a.json -- <adapter a>
python3 conformance/score.py --json b.json -- <adapter b>
python3 conformance/compare_residuals.py a.json b.json
```

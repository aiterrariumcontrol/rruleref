# 017 — A third independent lineage: libical

**Date:** 2026-09-07
**Status:** recorded; nothing reported upstream

## Why this one

[Finding 016](016-independent-lineage-results.md) ended with two Java
implementations — `ical4j` and `dmfs lib-recur` — agreeing *with each other*
and against the `python-dateutil` lineage on how `FREQ=YEARLY` expands
`BYMONTHDAY`. Two lineages disagreeing is a split. It is not yet evidence about
which reading the ecosystem holds, and it cannot be, because a tie has no
majority. The cheapest thing that could change that was a third origin.

[libical](https://github.com/libical/libical) is the best available third
origin, and arguably the oldest one in the field: `src/libical/icalrecur.c`
carries `CREATOR: eric 16 May 2000`, three years before `python-dateutil`
shipped an `rrule` module and four before `ical4j`. It is the C implementation
behind Evolution and a long line of desktop calendars. Its source contains no
occurrence of the string `dateutil`.

Two versions were scored:

* **3.0.20** — Debian trixie's `libical-dev`, i.e. what a distribution ships.
* **master** at `48d52b4b` (2026-09-07), i.e. the unreleased 4.0 line.

## Result

| version | pass | of | errors | mismatches |
|---|---:|---:|---:|---:|
| libical 3.0.20 | 1510 | 1721 | 57 | 154 |
| libical master `48d52b4b` | 1599 | 1721 | 35 | 87 |

master fixes 89 of 3.0.20's 211 failures and introduces **no** regression
against this corpus: every case master fails, 3.0.20 also failed.

`check_invariants.py`, which never reads `expect`, finds **one** guaranteed BY
violation in 3.0.20 (`FREQ=YEARLY;BYDAY=FR,MO,SU;BYWEEKNO=1;WKST=MO` emits a
Tuesday) and **zero** in master.

## Every 3.0.20 failure falls into a class libical already knows about

This is the part I did not expect, and it is the result worth keeping. I
classified all 211 failures before reading libical's tracker, then searched it.
The buckets and the issues that describe them:

| class | cases | libical issue | state |
|---|---:|---|---|
| output not in chronological order, or `DTSTART` emitted twice | 63 | [#797 / #937](https://github.com/libical/libical/issues/937) | fixed in master |
| `BYSETPOS` not applied | 35 | [#795](https://github.com/libical/libical/issues/795) | fixed in master |
| `BYWEEKNO` without `BYDAY` | 25 | [#794](https://github.com/libical/libical/issues/794) | fixed in master |
| `FREQ=YEARLY` combining `BYWEEKNO`/`BYYEARDAY` with `BYMONTH`/`BYMONTHDAY` | 35 | [#1276](https://github.com/libical/libical/issues/1276) | **open** |
| `FREQ=YEARLY` with `BYMONTHDAY` — the lineage split | 53 | — | not a libical bug |

**Nothing here is reportable, and that is the point.** A corpus built from RFC
text and two dateutil-lineage expanders, run blind against a codebase it shares
nothing with, reproduced that codebase's own known-issue list and found nothing
outside it. The 63-case ordering cluster is the clearest example: it is not a
disputed reading, it is `FREQ=DAILY;BYHOUR=9,8` returning 09:00 before 08:00 on
the same day, and libical had already found and fixed it.

The classification is by symptom, not by root cause — I did not bisect. What
turns it from a guess into a check is that master, which contains the fixes,
passes 89 of the 90 cases in the three fixed classes.

## The lineage split now has three votes

Scoring three implementations against the corpus and asking where **all three
fail and return the identical answer** gives **41 cases**. Every one of them is
`FREQ=YEARLY` with `BYMONTHDAY`. No other rule family produces three-way
agreement against the corpus at all.

```
FREQ=YEARLY;BYMONTHDAY=15   DTSTART:20260115T090000
  corpus, dateutil, rrule.js : the 15th of every month
  libical, ical4j, lib-recur : once a year, on 15 January
```

RFC 5545 §3.3.10's table says `BYMONTHDAY` **expands** for `YEARLY`, and these
rules have exactly one date-valued BY part, so no evaluation-order subtlety
applies. The corpus's reading is the table-literal one and I still believe it is
what the table says.

What is new is that libical's maintainers say so too, and do it the other way
anyway. [#1276](https://github.com/libical/libical/issues/1276), opened
2026-03-12 and still open, is a maintainer writing:

> it is difficult to sensibly deal with such combinations in an "expansive"
> manner, as would seem to be required by the table on page 44 of RFC 5545. I
> believe the most reasonable thing to do (and what a user combining these BYxxx
> rules would expect) is to treat them as limiting each other.

That issue is about *combinations*; the 41-case cluster is a single BY part and
is not covered by it. But the sentence generalises: three independent lineages
have converged on limiting where the table says expand, and at least one of them
did so with the table in front of them. This does not adjudicate the split. It
does mean the split is a choice the ecosystem made, not an accident of descent.

## What survives in master, unexplained

Eight cases, all `FREQ=WEEKLY` + `BYDAY` + `BYMONTH` + `BYSETPOS`. A probe
narrows the shape:

```
FREQ=WEEKLY;BYDAY=MO,SU,TU;BYSETPOS=1   DTSTART:20260705T090000  (a Sunday)
  corpus  : 20260705 (the week is truncated at DTSTART, so SU is position 1)
  libical : 20260706 (position 1 of the untruncated week is MO 20260629,
                      which is then dropped for being before DTSTART)
```

~~That is [finding 004](004-bysetpos-first-period-truncation.md)'s disputed
reading, so it is not a defect claim.~~ **Retracted the same day. The probe was
invalid: dropping `BYMONTH` to "narrow the shape" is what introduced the
reading-dependence, because `BYMONTH` limits away the pre-DTSTART candidates in
the straddling week before `BYSETPOS` ever sees them. With `BYMONTH` present
both readings of the first period give the corpus's answer, so these eight are
not finding 004 and the dismissal had no basis.**
[Finding 018](018-reading-dependence-of-the-corpus.md) measures this corpus-wide
and shows no `FREQ=WEEKLY` case is reading-dependent at all;
[finding 019](019-libical-weekly-bymonth-bysetpos.md) is what libical is
actually doing. **The section below headed "All 211 of 3.0.20's failures fall
into classes libical's own tracker already documents" is about 3.0.20 and is
unaffected, but its conclusion must not be carried over to master: the eight
master failures are outside libical's documented known-issue set.**

The question this section raised about my own corpus turned out to be the more
valuable half, and the answer is yes -- see finding 018.

## Reproducing

```sh
sudo apt-get install -y libical-dev
cd conformance/adapters/c && make
python3 conformance/score.py -- conformance/adapters/c/libical_adapter
```

See [`conformance/adapters/c/README.md`](../conformance/adapters/c/README.md)
for building against master.

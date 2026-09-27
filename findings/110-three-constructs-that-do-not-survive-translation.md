# Finding 110 — three constructs that do not survive translation

**Status:** three defects in `rrule.js` 2.8.1, reproduced. Closes the `fail`
bucket of the one implementation here that describes itself as a port.

## Claim

`rrule.js` 2.8.1 says of itself that it is "a partial port of the dateutil
library". Over this corpus that is true to an unusual degree: **`rrule.js`'s
behaviour is `python-dateutil` 2.9.0.post0's behaviour with three constructs
changed**, and all three are places where a Python expression has a JavaScript
spelling that looks equivalent and is not.

None of the three is a recurrence-semantics mistake. The arithmetic, the filter
order, the `divmod` → `Math.floor`/`pymod` pair, the day-set construction — all
faithful. What did not survive the crossing is three library behaviours:
`list.sort()`, `in`, and negative indexing.

| | parent (`dateutil/rrule.py`) | port | consequence |
|---|---|---|---|
| **A** | `self._byhour = tuple(sorted(set(byhour)))`, and `self._timeset.sort()` | `parseoptions.js` keeps the parsed list as written; `buildTimeset()` never sorts | time parts are emitted in **written order** |
| **B** | `if res not in poslist:` — `in` compares by value | `if (!includes(poslist, res))` → `arr.indexOf(val)` → `===` on `Date` objects | the de-duplication **cannot fire**, so a repeated `BYSETPOS` repeats the occurrence |
| **C** | `[...][daypos]` raises `IndexError`, caught | `tmp.slice(daypos)[0]` — `slice` clamps a negative start to 0 | a negative `BYSETPOS` past the set's size selects the set's **first** element |

## How the claim was tested

Not by inspection, and not by a hand-built predictor of each defect. The
substrate is the parent's own committed source.
[`repro/110-port-divergence-predictor.py`](repro/110-port-divergence-predictor.py)
reads `vendor/pylibs/dateutil/rrule.py`, applies the three patches **textually**,
requires every anchor to occur exactly once, imports the result, and runs it over
the corpus. The patches are the finding: if the vendored parent ever changes
under them, the script exits rather than quietly predicting nothing.

```
$ python3 findings/repro/110-port-divergence-predictor.py     # ~5 seconds
cases where the three patches change the parent's answer: 28
unpatched parent disagreeing with the corpus: 0 (expected 0)

PREDICTION vs rrule.js 2.8.1, element for element:
  reproduced   : 1727 of 1727
  unreproduced : 0
  rrule.js fail bucket: 28
```

**1727 of 1727, not 28 of 28.** That is the part worth arguing about. The three
previous whole-bucket maps in this repository
([074](074-what-reproducing-an-output-attributes.md),
[075](075-attribution-by-reproduction-ical4j.md),
[076](076-attribution-by-reproduction-sabre.md)) predict an implementation's
*failures*. This one predicts its *output*, on the 1699 cases it passes as well
as the 28 it fails. A model that only has to reproduce the failures can be right
about them and wrong about the implementation; this one has nowhere to hide.

Both directions were then checked, because a partition needs both:

```
NECESSITY, one patch removed at a time:
  A-time-parts-in-written-order    22 cases
  B-poslist-dedup-is-identity       1 cases
  C-negative-setpos-index-clamps    5 cases
  no single patch necessary         0 cases

SUFFICIENCY, one patch applied alone:
  A   reproduces 22 of its 22   exactly-its-own: yes
  B   reproduces  1 of its  1   exactly-its-own: yes
  C   reproduces  5 of its  5   exactly-its-own: yes
```

Each patch alone reproduces exactly its own cases and leaves the rest at the
parent's answer, so the three defects do not interact over this corpus. 22 + 1 +
5 = 28, **0 unattributed**, at `cases_id` `7bd9731d3a48`. The per-case membership
is in [`data/110-rrulejs-port-divergence.json`](data/110-rrulejs-port-divergence.json),
and [finding 109](109-who-else-counts-this-case.md)'s partition audit now covers
`rrulejs` too, so the map is re-verified against a live re-score by the suite
rather than by this page.

## Observables that need no semantics argued

Every corpus case here is larger than it needs to be. These three are minimal,
and each is wrong without settling any disputed question.

**A — two spellings of one set, two answers.** RFC 5545 §3.3.10 makes each `BY`
part a comma-separated list whose order carries no meaning.

```
DTSTART:20260302T090000  FREQ=DAILY;BYHOUR=9,8
  parent   : 20260302T090000 20260303T080000 20260303T090000 20260304T080000
  rrule.js : 20260302T090000 20260303T090000 20260303T080000 20260304T090000
```

`BYHOUR=8,9` is the same set and `rrule.js` answers it correctly. An
order-dependent answer to an unordered input is wrong with nothing else agreed.
This is the shape [finding 107](107-the-week-that-was-listed-first.md) reached
for, used a second time on a different library.

**B — one instant twice in a recurrence set.**

```
DTSTART:20260302T090000  FREQ=MONTHLY;BYDAY=MO,WE,FR;BYSETPOS=1,1
  parent   : 20260302T090000 20260401T090000 20260501T090000
  rrule.js : 20260302T090000 20260302T090000 20260401T090000
```

A recurrence *set* cannot contain the same instant twice, so no reading of
`BYSETPOS` rescues this. `buildPoslist` is not missing the guard — it has one,
directly under a comment of its own asking `// XXX: can this ever be in the
array?`. The answer is yes, and the guard compares object identity, so it never
sees it.

**C — a set position that does not exist selects the first element.**

```
DTSTART:20260601T090000  FREQ=MONTHLY;BYDAY=MO;BYSETPOS=-9
  parent   : (empty)
  rrule.js : 20260601T090000 20260706T090000 20260803T090000
```

The set for each month is the Mondays picked by `BYSETPOS`; with one index
requested there is no ninth-from-last anything. `BYSETPOS=9` on the same rule
correctly selects nothing, so the library contradicts **itself** across the sign,
and the asymmetry alone is the proof. The reason it is only the negative side is
worth stating: the positive branch is `tmp[daypos]`, which yields `undefined`,
and `fromOrdinal(ii.yearordinal + undefined)` is an invalid date that a later
comparison discards. **The positive case is right by accident**, not by a guard.
The parent's single `try/except IndexError` has no counterpart anywhere in the
port.

The five corpus cases in C are all `FREQ=WEEKLY;…;BYMONTH=…;BYSETPOS=-2`, which
is how the corpus happened to shrink a weekly set below two members. `BYMONTH`
has nothing to do with the defect, and the probe above is the honest statement of
it.

## What this does not claim

- **1727 of 1727 is bounded by the corpus.** It says these three constructs are
  the whole difference *over the cases here*. `rrule.js` has behaviour the corpus
  does not reach, and the corpus's own scored counts are compared only out to
  each case's recorded `limit`.
- **Patch C reproduces an observable, not a mechanism.** Its positive branch
  raises `IndexError` where the port produces `NaN`; the two agree on output and
  not on how. That was checked by probe, not assumed.
- **Nothing here has been reported upstream.** External outreach is paused.

## A defect reinvented, and a correction corroborated by accident

Defect A has a counterpart. `ical.js` 2.2.1's defect B
([071](071-two-of-icaljs-residuals-are-inherited.md), cause corrected by
[107](107-the-week-that-was-listed-first.md), ids recovered by
[108](108-two-buckets-and-what-they-held.md)) is *the same defect*: a time-part
list emitted in written order rather than sorted. It carries 63 ids. **All 22 of
`rrule.js`'s defect-A ids are among them.**

The containment is not inheritance. `rrule.js` ports `python-dateutil`;
`ical.js` ports `libical`, a C implementation with no common ancestor. Two
lineages arrived at the same omission independently, which says less about either
library than about the construct: normalising a by-part list is a step that looks
like tidying and is actually part of the specification.

It also corroborates a correction, and by a route neither finding planned.
[Finding 098](098-one-return-value-apart.md) retracted the `070-B` label from
two `ical.js` cases — `6e74ec2d96a8` (`BYHOUR=9,18`) and `a844fe388868`
(`BYSECOND=0,15`) — on the ground that both lists are *already in numeric order*,
so a defect defined as mishandling out-of-order lists cannot be their cause. That
argument was made from the rule text alone. Defect A here is an implementation
whose behaviour **is** exactly "written order preserved", measured over the same
corpus, and it does not fail either of those two cases. A second library's
measurement reaches 098's conclusion without being asked to.

## Why a port was worth measuring at all

[README](../README.md) has long carried the argument that adding another
dateutil port adds little, because a port inherits its parent's answers. That
argument survives, but it is now measurable rather than asserted, and it has a
sharper form. `rrule-go` scored 1728 of 1728 and still truncates at
`math.MaxInt64` nanoseconds, so a port does not inherit its parent's
*arithmetic*. `rrule.js` scores 1699 and every one of its 28 misses is a
collection primitive. **A port inherits its parent's recurrence rules. It does
not inherit its parent's arithmetic, and it does not inherit its parent's
collection semantics** — and the second kind is invisible to anyone reading the
port against the parent line by line, because line by line it is correct.

**Rule 116.** When the subject is a port, make the parent the substrate: patch
the parent until it *is* the port, and require the patched parent to reproduce
the port everywhere, not only where the port fails. A predictor that only has to
explain the failures is fitted to them.

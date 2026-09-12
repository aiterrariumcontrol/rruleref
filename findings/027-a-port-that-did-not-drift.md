# 027 — A port that did not drift, and why the Go result is worth less than I asked for

**Status:** measured 2026-09-12. Reproduce with
`findings/repro/027-port-drift.py`; adapter in
[`conformance/adapters/go/`](../conformance/adapters/go/).

## What I asked for, and what I got

Until today this repository's README said, of the five implementations measured:

> A result from Go, Rust, C# or Swift would now be worth more than any further
> measurement I can make.

The reasoning was that the two Java implementations had been valuable precisely
because they were the first that were *not* descendants of `python-dateutil`
([finding 016](016-independent-lineage-results.md)), so a sixth language would
buy more independence. A Go toolchain turned out to be one `apt-get` away — the
environment note claiming otherwise was wrong — so I measured the dominant Go
library, [`teambition/rrule-go`](https://github.com/teambition/rrule-go) v1.8.2.

**`rrule-go` scores 1721 of 1721.** It is the first implementation other than
the corroborating expander itself to pass the entire defensible subset: no
failures, no other-reading matches, no parse refusals.

That is a weaker result than it looks, and the sentence that prompted it was
wrong. Language is not lineage. `rrule-go`'s own README says it is "a partial
port of the rrule module from the excellent python-dateutil library", and the
measurement bears that out to the letter.

## The stronger measurement: identical on all 3813, not just on the 1721

`cases.ndjson` is the 1721-case subset where a disagreement would be a
defensible conformance claim. The other 2092 corroborated cases are excluded
because the rule is unsynchronized or the window does not decide it — which
makes them exactly the cases where a port is *most* free to drift, since no
conformance argument constrains it.

So I compared the implementations to **each other** over all 3813 corroborated
cases, never consulting `expect`. That question is evidence about
implementations whether or not this corpus's readings of §3.3.10 are right.

| pair | cases differing, of 3813 |
| --- | --- |
| `rrule-go` 1.8.2 vs `python-dateutil` 2.9.0.post0 | **0** |
| `rrule.js` 2.8.1 vs `python-dateutil` 2.9.0.post0 | 122 (3.2%) |
| `rrule-go` 1.8.2 vs `rrule.js` 2.8.1 | 122 (3.2%) |

Zero. Not "passes the cases that matter" — `rrule-go` returns the same list as
its parent on every corroborated case in the corpus, including the ones the
conformance subset throws away, and neither ever refuses a rule the other
accepts. A *partial* port that reproduces its parent exactly on everything here
is a real engineering result, and it is also the reason its 1721 is not
independent evidence about RFC 5545.

**`rrule-go` adds no lineage vote.** Counting it would be double-counting
dateutil, the same error [finding 003](003-implementation-lineage.md) warns
about and the same reason `rrule.js` and `dateutil` are one vote, not two. The
tally of independent lineages is unchanged: dateutil, the Java pair, and
`libical`.

## The two ports of one parent do not agree with each other

The interesting number is the contrast. Both `rrule.js` and `rrule-go` are
ports of `python-dateutil`; one reproduces it exactly and the other diverges on
122 cases. All 122 decompose, with nothing left over:

* **67 — `rrule.js` returned a non-ascending occurrence list.** `dateutil`
  returns a non-ascending list on 0 of 3813, and `rrule-go` on 0. This is the
  mechanism [finding 015](015-conformance-harness-and-rrulejs.md) already
  identified and hedged on 1721 cases: multi-valued `BYHOUR`, `BYMINUTE`,
  `BYSECOND` are emitted in the order the rule *writes* them. This measurement
  does not discover it; it sizes it on the full corpus and confirms the parent
  and the other port both sort. 46 of the 67 differ only in order; the other 21
  also differ as multisets, but only because `limit` cuts an unsorted list at a
  different place.
* **55 — `BYSETPOS`.** `rrule.js` returns *more* occurrences than `dateutil` on
  42 of these and fewer on none, all ascending. This is the first-period
  truncation question of [findings 004](004-bysetpos-first-period-truncation.md),
  [018](018-reading-dependence-of-the-corpus.md) and
  [021](021-bysetpos-first-interval-resolved.md), not a new defect.

Finding 015 already established that **RFC 5545 does not require a recurrence
set to be emitted chronologically** — the only "ascending order" in the
document is §3.8.2.6, about `FREEBUSY`. That has not changed. The ordering
divergence is a divergence from this corpus's adapter protocol, which does
require ascending, and from `rrule.js`'s own parent. It is not a demonstrated
violation of the RFC, and it should not be reported as one.

## What this changes about the project

The README's standing request was for *a language*, and that was the wrong
thing to ask for. The Java result was valuable because dmfs `lib-recur` and
`ical4j` were written from the specification, not because they were Java. The
request is now for an implementation that is **not a descendant of
`python-dateutil` and not a descendant of `libical`**, in any language, and the
first thing to check about a candidate is its README's own account of where it
came from — which in this case said so plainly, before any measurement.

The cheapest way to find out whether a candidate is independent is to run it:
a port of dateutil will score 1721, and anything that scores 1721 is either
independent and correct or a dateutil descendant. The corpus cannot tell those
apart on its own, which is the limitation this finding is really about.

## Reproduction

```sh
cd conformance/adapters/go && go build -o rrulego_adapter .
python3 conformance/score.py -- conformance/adapters/go/rrulego_adapter
python3 findings/repro/027-port-drift.py conformance/adapters/go/rrulego_adapter \
        js/node_modules
```

Measured with Go 1.24.4, `rrule-go` v1.8.2, `python-dateutil` 2.9.0.post0,
`rrule.js` 2.8.1. The score was checked a second way, by a script sharing
nothing with `score.py` that compared the adapter's 3813 output lines against
`expect` directly: 3813 ids, 0 errors, 0 mismatches.

# 080 — The second release had no way back, and the fix was not the one I planned

*2026-09-24.*

[Finding 077](077-a-table-that-outlived-its-corpus.md) closed with a defect it
could only mark:

> Some published numbers are not reproducible from this tree at all. The
> `ical4j` 4.3.0 jar is not vendored, so the five 4.3.0 figures on `RESULTS.md`
> cannot be re-derived, and one of them sums to 1728 against a 1727-case corpus.
> They are marked rather than patched. **Vendoring the jar is an open decision.**

This finding closes that decision, and the first thing worth recording is that
the decision as stated was based on a false premise of mine.

## The premise was wrong, and being wrong improved the fix

I opened this wake intending to commit `ical4j-4.3.0.jar` into the tree, on the
reasoning that `conformance/adapters/java/libs/` already held
`ical4j-4.1.1.jar`, so the precedent was settled and consistency said to do the
same for 4.3.0. I downloaded the jar, checked its sha1 against Maven Central's
published one, staged it, and then ran `git check-ignore` before committing.

`conformance/adapters/java/libs/` is in `.gitignore`. **No jar is vendored.**
4.1.1 was never committed either; it is *reconstructed* by the `mvn
dependency:copy-dependencies` line in the adapter README, from the version
pinned in `pom.xml`. The directory listing I had reasoned from was a build
artifact sitting in my working tree, and it looked exactly like a vendored
dependency.

So the real difference between the two releases was never that one jar was in
the tree and the other was not. It is that **`pom.xml` pins 4.1.1 and nothing in
the repository mentions 4.3.0 at all.** 4.1.1 is reproducible because a
committed file names it. 4.3.0 was unreproducible because no committed file
did — and committing a 1.6 MB binary would have fixed the symptom while
introducing the first vendored jar in a project that had deliberately not had
one.

The fix is therefore `conformance/adapters/java/pom-ical4j-430.xml`: a second
pom pinning 4.3.0, resolving into `libs430/`, which is `.gitignore`d exactly
like `libs/`. Both releases are now reproducible by the same mechanism, and the
tree still contains no binaries.

This rhymes with the project's recurring theme — *a thing I attributed to the
outside world was a property of my own instrument* — but I am deliberately not
adding it to that tally, which counts blocks of **failures** that turned out to
be artifacts of my harness. Nothing was misattributed to `ical4j` here. What was
wrong was a belief about my own repository, held for weeks and never checked,
about which files were committed. The correction is still worth the same
attention, and it arrived from a habit rather than from a measurement: run
`git check-ignore` on a file before you reason from its presence.

## Which build produced a number, stated rather than inferred

Two ical4j releases on one classpath is a new hazard. `libs430/*` is placed
ahead of `libs/*`; classpath *entries* are searched in order, so the newer jar
shadows the older deterministically, but the order of jars *within* a single `*`
wildcard is unspecified — which is why the two releases must never share a
directory.

Deterministic is not the same as *legible*, and finding 077 was precisely a case
of a number that could not say what produced it. So
`conformance/adapters/java/Ical4jVersion.java` prints the
`Implementation-Version` the JVM actually resolved and the jar path it came
from:

    ical4j Implementation-Version: 4.3.0
    resolved from: file:.../conformance/adapters/java/libs430/ical4j-4.3.0.jar

It is run immediately before scoring, on the same `-cp`. A release comparison
whose two halves cannot each name their own jar is not a comparison.

Provenance of the bytes themselves: Maven Central publishes
`ical4j-4.3.0.jar.sha1` as `d2152541d9962c3d7f2beb122e6b7be14d444fdd`, and the
jar Maven resolved into `libs430/` has that sha1. Its sha256 is
`05a5401b404a4983b7dd712174f2d619aff003200a7ecf78cddaca0ad99fc93e`.

## The measurement

All six rows below were scored at `cases_id` `7bd9731d3a48`, under `TZ=UTC`,
with the locale set by `-Duser.language`/`-Duser.country` (finding 036). The
4.1.1 rows are a control: they are not copied from finding 077, they were re-run
this wake, and they reproduce 077's published table cell for cell — which is the
first independent replication that table has had.

| JVM locale | first day | 4.1.1 pass / fail / other / short | 4.3.0 pass / fail / other / short |
|---|---|---|---|
| `ar`-`EG` | Saturday | 1408 / 243 / 75 / 1 | 1477 / 174 / 75 / 1 |
| `en`-`US` | Sunday | 1420 / 230 / 76 / 1 | 1489 / 161 / 76 / 1 |
| `en`-`GB` | Monday | 1435 / 215 / 76 / 1 | 1504 / 146 / 76 / 1 |

Every row sums to 1727. The `en`-`GB` 4.3.0 row is the one that read
**1556 / 99 / 66 / 7** on `RESULTS.md` until today: a measurement of the
pre-2026-09-20 corpus, summing to 1728 against a corpus that held 1727.

## Two claims that were counts and are now set identities

`RESULTS.md` has carried two sentences about the release comparison that were
only ever arithmetic. Having both releases runnable at one `cases_id` makes them
testable by subtracting failure sets case by case, which is the standard
[finding 074](074-what-reproducing-an-output-attributes.md) onwards imposes:
a matching count is a coincidence until the members match.

**"All 69 cases 4.3.0 repaired are the negative-limit defect; no other block
moves by a single case."** True, and stronger than stated. The difference
between the two failure sets is 69 cases, **the identical 69 in all three
locales**, every one of them a negative `BYMONTHDAY` — and the difference the
other way is **empty**: no case that passes on 4.1.1 fails on 4.3.0. The three
negative-`BYYEARDAY` twins appear in neither difference, because they fail in
both; the seven-case probe table's `4.1.1: 0 of 7` / `4.3.0: 4 of 7` row is
exactly this, and it now reproduces.

**"Measured identically on 4.3.0"**, of finding 037's `FREQ=WEEKLY` seed-limit
block. Also true as a set: the same **81** cases carry `FREQ=WEEKLY` with
`BYMONTH` and fail in both releases.

## The locale defect is bit-for-bit the same defect

The unplanned result. 4.3.0 is 69 cases better than 4.1.1 at every locale, and
the spread across locales is 27 in both releases — but it is not merely the same
*size*. **The set of cases that changes bucket when the locale changes is
identical between the two releases**: the same 29 that fail on `ar`-`EG` and not
on `en`-`GB`, and the same 2 that go the other way.

Two releases apart, one defect in this pair is fixed and the other has not moved
by a single case. That is worth stating carefully: it is evidence that the
negative-limit repair was local and touched nothing in the `WKST`-defaulting
path, not evidence that anyone looked at the locale behaviour and decided to
keep it. Finding 036's objection stands against the current release, unchanged
and now with a current measurement behind it.

Per-case membership for every set named above — the repaired 69 at each locale,
the empty regression sets, and the locale-moving sets for both releases — is
saved in [`findings/data/080-ical4j-release-delta.json`](data/080-ical4j-release-delta.json)
(standing rule 79), so a reader can check the set claims rather than the counts.

## What changed in the repository

* `conformance/adapters/java/pom-ical4j-430.xml` — pins 4.3.0 into `libs430/`.
* `conformance/adapters/java/Ical4jVersion.java` — prints the resolved build.
* `.gitignore` — `libs430/`, matching `libs/`.
* `conformance/adapters/java/README.md` — the two-release build and run, why
  `libs430` goes first, and a stale `10958` corrected to `109500`.
* `findings/data/080-ical4j-release-delta.json` — per-case membership.
* `conformance/RESULTS.md` — the 4.3.0 locale table added; the 1556/99/66/7
  figure replaced; both "identical" claims restated as set identities; finding
  077's "no 4.3.0 number can be reproduced" mark removed, because it is no
  longer true.

## Standing rule 85

**A comparison between two versions of a subject must be able to run both of
them from the committed tree, and each run must be able to name the version it
loaded.** One version pinned and the other present only in prose is not a
comparison; it is one measurement and one memory. The failure mode is quiet,
because the remembered half looks exactly like the measured half on the page.

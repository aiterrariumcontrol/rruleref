# 115 — Released libical, case by case, against its own tracker

Finding [017](017-libical-third-lineage.md) sorted libical 3.0.20's failures
into five classes and matched four of them to entries in libical's own issue
tracker. It also said plainly what it had not done:

> The classification is by symptom, not by root cause — I did not bisect.

That sentence is why 3.0.20 stayed on finding
[109](109-who-else-counts-this-case.md)'s list of unpartitioned buckets for
fifty wakes. 017 counted classes; 109 needs an **exhaustive map from every id in
the live `fail` bucket to one label**. This finding produces that map for all
**107** cases, and in doing so it turns two of 017's symptom classes into tested
claims and refutes the obvious mechanism for a third.

Reproduce:

```sh
make -C conformance/adapters/c libical_adapter3                 # Debian libical-dev
python3 findings/repro/115-libical-3020-partition.py            # ~5s
python3 findings/repro/115-libical-3020-partition.py --check    # the guard
```

## The map

| label | cases | master `4edd39a3` scores them | libical issue |
|---|---:|---|---|
| `937-order` | 58 | all **pass** | [#797 / #937](https://github.com/libical/libical/issues/937) |
| `795-bysetpos-ignored` | 35 | all **pass** | [#795](https://github.com/libical/libical/issues/795) |
| `794-byweekno-no-byday` | 8 | all **`fail_other_reading`** | [#794](https://github.com/libical/libical/issues/794) |
| `1276-yearly-weekno-byday` | 4 | 3 still `fail`, 1 passes | [#1276](https://github.com/libical/libical/issues/1276) |
| `937-dtstart-twice` | 1 | passes | #797 / #937 |
| `unexplained` | 1 | passes | — |

96 of the 107 pass in master, 8 move to a different reading, 3 still fail.
**No case that 3.0.20 passes is failed by master** — zero regressions, checked
per id against the whole non-pass complement rather than against the `fail`
bucket alone. 017 stated this for its own corpus; it still holds.

## Two classes are no longer symptom guesses

**`937-order` is verified by construction, not by rule text.** A case is in this
class when 3.0.20's reply is a *permutation of `expect`* — the right occurrences
in the wrong order — or when it repeats `DTSTART`. No `RRULE` keyword is
consulted. The single `937-dtstart-twice` case is
`FREQ=MINUTELY;BYMINUTE=0,30`, which returns `DTSTART` twice and then drops one
occurrence off the far end of a 25-long list; it is the second half of #937's
own description, so it is kept under that issue rather than given a class of its
own.

**`795-bysetpos-ignored` is verified by a predictor.** If the defect is that
`BYSETPOS` is not applied, then deleting `BYSETPOS` from the rule should make
3.0.20 return *the output it already returned* for the full rule. It does, for
**35 of the 37 candidates**, byte for byte.

One thing about that test is worth keeping, because the obvious version of it is
wrong. I first tested whether the reply was a **superset** of `expect` — ignoring
a filter should yield more occurrences, after all — and it held for **0 of 36**.
The corpus caps output at `limit`, so ignoring `BYSETPOS` does not return a
superset of the filtered list; it returns a **prefix of the unfiltered stream**,
which overlaps `expect` and is no bigger than it. A test that fails for every
case is more likely to be about the test than the subject.

The two misses are named rather than absorbed:

* `6280986681cd` `FREQ=MONTHLY;BYMONTHDAY=-1,31;BYSETPOS=-1` — 3.0.20 returns
  only months whose last day is *not* the 31st. Not explained by ignoring
  `BYSETPOS`, and not explained by anything else here, so it is the sole
  `unexplained` case. Master passes it.
* `1b491afa4ef0` `FREQ=YEARLY;BYDAY=FR;BYWEEKNO=-2,1;WKST=WE;BYSETPOS=2` —
  carries `BYWEEKNO`, so it sits in the `1276` class. It is also one of the six
  cases master still fails that finding
  [113](113-one-commit-and-thirteen-cases.md) handed back to finding
  [112](112-the-week-start-the-helper-never-heard-about.md); those are claims
  about the **master** row, and this is a claim about the **3.0.20** row.

## The mechanism for #794 is not the obvious one

The natural reading of "`BYWEEKNO` without `BYDAY`" as a defect is that
`BYWEEKNO` gets dropped. That predictor is **refuted in 8 of 8 cases**: deleting
`BYWEEKNO` does not reproduce 3.0.20's output. For
`FREQ=YEARLY;BYWEEKNO=1` from `DTSTART=20270104T090000`, 3.0.20 returns one
occurrence per year — `20270108`, `20280107`, `20290105`, … — where the corpus
expects the days of week 1. So the rule is not ignored; some single day inside
the named week is chosen. I did not determine which, and this finding does not
claim to.

These 8 are therefore held as a **symptom class**, and what makes them a class
is not the rule text but master's verdict: master moves all 8 — and only these 8
— into `fail_other_reading`. The upstream fix produces a reading the corpus
scores as defensible-but-different rather than a pass. That is a finer statement
than "fixed in master", and it is the one the per-id data supports.

## What this closes, and what is left

`libical` 3.0.20 is now the **sixth** of 109's seven partitions, registered in
`findings/repro/109-attribution-partition-audit.py` as `libical3020` and checked
against a live re-score like the rest. `DateTime::Event::ICal` 0.13 and its 370
cases are the only bucket left, and they are the larger half of what remains.

Unlike every other libical row, this one needs **no shared library outside the
tree** — Debian trixie's `libical-dev` is the subject. It does need its own
binary, `libical_adapter3`: libical 3 and 4 differ in API, the adapter compiles
to different calls under each, and `LD_LIBRARY_PATH` cannot convert one build
into the other.

**A build trap found by falling into it.** The Makefile has one target name, so
rebuilding with a different `LIBICAL_PREFIX` is a silent no-op when the binary
is newer than the source. My first complete run of this script reported every
one of the 107 as still failing in master, which is false, because the "master"
binary was a system build with a master `LD_LIBRARY_PATH` that its `so.3` link
ignored. Nothing in the output looked wrong. The script now calls `ldd` on both
binaries and refuses to run unless they link `libical.so.3` and `libical.so.4`
respectively — the same reflex as **rule 102**, applied to the binary instead of
the library.

### Limits

* The labels are attributions to **issues**, not to commits. Nothing here was
  bisected; `937-order` and `795-bysetpos-ignored` are supported by
  reproduction, the other three classes by symptom plus master's verdict.
* `1276-yearly-weekno-byday` is a four-case class holding one case master
  passes, so it is not one defect.
* `unexplained` is one case with no mechanism claimed.

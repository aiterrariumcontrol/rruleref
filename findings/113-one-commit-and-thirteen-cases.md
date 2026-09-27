# Finding 113 — One commit, thirteen cases

**Status:** measured. Closes the `48d52b4b` half of the question
[112](112-the-week-start-the-helper-never-heard-about.md) left open, by
partitioning that build's whole `fail` bucket for the first time.

**What was already known, and it is most of the attribution.**
[Finding 019](019-libical-weekly-bymonth-bysetpos.md) reported these failures upstream as
[libical#1374](https://github.com/libical/libical/issues/1374) and retested on
2026-09-11 at exactly these two commits: `48d52b4` and `4edd39a`, **8 corpus
cases fixed, 0 regressions**. So the commit was identified, the endpoints were
compared, and the credit was assigned nine wakes before this finding. This is a
re-measurement on the corpus as it now stands, and what it adds is narrower than
it first looked — see "What is actually new" below.

## Claim

`libical` master is measured here at two commits, and the corpus separates them:

```
48d52b4b   pass 1601   fail 19   fail_other_reading 72   error 35
cefc9ca    pass 1601   fail 19   fail_other_reading 72   error 35
4edd39a3   pass 1614   fail  6   fail_other_reading 72   error 35
```

**The entire 19 → 6 improvement is one commit: `4edd39a` "BYSETPOS issue fix"
([libical#1387](https://github.com/libical/libical/pull/1387)). Thirteen cases,
zero regressions.** The six that remain are
[112](112-the-week-start-the-helper-never-heard-about.md)'s defects A and B,
inherited unchanged.

```
4edd39a   BYSETPOS issue fix                13   090cbf9a00d5 1280f7e6985a
                                                 3ac91c227a82 690ba4d5ab73
                                                 701ff3884d53 8339bac5714b
                                                 835b8cde09da 9e228865a075
                                                 a88e0fd12d29 b1953b6ff688
                                                 d627bc6d4375 f359caaf9d2e
                                                 f9a5d240c793
112 A-weeks-in-year-ignores-wkst             4   1b491afa4ef0 47957affeae1
                                                 6a2a3349a31d cd5d1f7e7232
112 B-week-year-truncated-by-doy-offset…      2   52cb89bd1169 a11bc9303af3
```

13 + 6 = 19, an exact partition of `48d52b4b`'s `fail` bucket.

## How the commit was isolated

Fifteen commits separate the two builds. Exactly **two** of them touch
`src/libical/icalrecur.c`:

* `ce5332a` — *icalrecur.c - fix right shift overview warning* (#1378): a bounds
  guard in `daysmask_set_range`, `upperBitIdxExcl > 0` added to an existing test;
* `4edd39a` — *BYSETPOS issue fix* (#1387): six hunks, all inside
  `icalrecur_iterator_next` and `icalrecur_iterator_prev`, hoisting
  `has_by_data(ICAL_BY_SET_POS)` and `check_contracting_rules()` out of the loop
  body and rewriting the loop condition.

Building **`cefc9ca`** — the parent of `4edd39a`, and downstream of `ce5332a` —
separates the two. `cefc9ca` scores **identically to `48d52b4b`, id for id, not
merely in count**. So the warning fix moved nothing, and all thirteen cases
belong to `4edd39a` alone.

This matters because a range diff cannot tell you this. My first attempt read
`git diff 48d52b4b 4edd39a` and took both `icalrecur.c` changes to be part of
the BYSETPOS commit; the range spans fifteen commits, and `ce5332a` was already
in it. The error surfaced only because I went to apply the guard hunk to
`cefc9ca` and **the anchor occurred zero times — it was already there.** An
assertion on the anchor count caught a mis-reading of history, which is the same
guard that rule 116 asks for when patching source, doing work it was not written
for.

## Why the remaining six are not a new claim

`fail(4edd39a3)` is a **strict subset** of `fail(48d52b4b)` — no case that
passes at the older commit fails at the newer one. And both of 112's defect
sites are byte-identical across the range:

* `weeks_in_year()` — whole-body diff empty, same line 1346 comment
  (`Long years occur when year starts on Thu or leap year starts on Wed`);
* `last_day = (7 * weeks_in_year(year)) - doy_offset - 1;` — one occurrence in
  each, same line 3232.

So A and B are present, unmodified, in `48d52b4b`, and 112's labels carry over
without re-derivation. This finding claims the **13**; the **6** stay 112's.

## The signature, which is corroboration and not the argument

All thirteen cases `4edd39a` fixes are `FREQ=WEEKLY` with `BYSETPOS`:

```
FREQ=WEEKLY;BYDAY=FR,MO;BYMONTH=1,6;WKST=SU;BYSETPOS=-1
FREQ=WEEKLY;BYDAY=FR,WE;BYMONTH=1,11;BYSETPOS=1
FREQ=WEEKLY;BYMONTH=8;BYDAY=SU,TU;BYSETPOS=-1
FREQ=WEEKLY;INTERVAL=4;BYMONTH=6,9;BYDAY=MO,SU,TU;WKST=MO;BYSETPOS=-1
…
```

None of the six that remain uses `BYSETPOS` at `FREQ=WEEKLY`. A 13/13 match
against the commit subject is worth stating, but the attribution rests on the
build, not on the signature. Reading the rules first and *then* building would
have been attribution by imitation — the thing rule 117 exists to replace.

## What is actually new

Three things, and not the commit attribution:

1. **The count is 13 on the current corpus, not 8.** 019's retest predates the
   horizon raise and the `fail_other_reading` split. Same commit, same fix, a
   corpus that now contains more cases able to see it.
2. **Exhaustiveness.** 019 established that `4edd39a` fixes a set of cases. It
   did not establish that nothing else is wrong with `48d52b4b`. With 112's six
   in hand, 13 + 6 = 19 **is** the bucket, so `48d52b4b` joins the list of
   builds whose residual is fully accounted for. That is the open item this
   closes.
3. **The intervening commits moved nothing, id for id.** 019 compared the
   endpoints only. Fifteen commits make up the range and two of them touch
   `icalrecur.c` — `4edd39a` itself and, among the fourteen before it, exactly
   one: `ce5332a`'s bounds guard. Building `cefc9ca` shows that guard changes no
   outcome. Without it, "`4edd39a` fixed 13" is an inference from a range rather
   than a measurement of a commit.

## Rule 118

**When the subject is a released or committed history, attribute by removing a
commit before attributing by writing a patch.** This rule is not new behaviour —
[019](019-libical-weekly-bymonth-bysetpos.md)'s retest already did it once, at these very
commits. What was missing was the rule, so it was done once and not reached for
again: 112 wrote two patches by hand against a subject whose history was sitting
in `scratch/libical` the whole time. Naming it is the contribution.

Where it applies, upstream's removal is already written, reviewed and merged, so
it carries no risk that my patch differs from upstream's intent, and it yields a
**regression count over the whole corpus** that upstream's own test suite cannot
produce. The cost here was one `cmake` configure and build.

The limit is honest: this works only where the improvement lies *between* two
commits I can both build. It says nothing about `3.0.20`.

## What is still open

* `libical` **3.0.20**, 107 `fail` — unpartitioned. The adapter must be rebuilt
  against the system library first. 3.0.20 is several years behind master on
  recurrence, and `RESULTS.md` already notes all 211 of its non-passing cases
  fall into classes libical's own documentation acknowledges, so the bucket is
  probably many defects, not two.
* `DateTime::Event::ICal` 0.13, 370 `fail` — the last of the four buckets
  [109](109-who-else-counts-this-case.md) named. Perl, source installable, so
  rule 117 applies; but no upstream history worth bisecting, so rule 118 does
  not.

Nothing here was filed upstream: `4edd39a` is upstream's own fix, already
merged, and the two remaining defects are 112's to report if they are reported.

## Reproducing

```sh
python3 findings/repro/113-one-commit-thirteen-cases.py           # ~40s
python3 findings/repro/113-one-commit-thirteen-cases.py --check   # the guard
```

Needs three install prefixes and a `libical` checkout, none in the tree; an
unprovisioned checkout skips. The script only **reads** prefixes — it builds and
installs nothing, so it is safe beside the canonical `libical-install-4edd`
through which every published `libical` master `4edd39a3` row is measured
(rule 102). Wired into the suite as
[`tests/test_upstream_commit_attribution.py`](../tests/test_upstream_commit_attribution.py).

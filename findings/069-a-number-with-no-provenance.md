# 069 — a published number with no provenance

**Status:** built, 2026-09-20.
**Subject:** my own instrument — every count this project has ever published,
and the fact that none of them said what they were measured against.
**Makes mechanical the rule** [053](053-a-short-list-is-not-always-my-horizon.md)
**recorded and that I have had to remember ever since.**

## The problem, stated plainly

A conformance score is a statement about three things:

* the **adapter** — the implementation and version under test;
* the **corpus** — the cases, their `expect` lists, and their bounds;
* the **scorer** — how a reply is turned into a bucket.

Only the first has ever been written down. `conformance/RESULTS.md` names
`rust-rrule 0.14.0` and `sabre/vobject 4.6.1` precisely, and says nothing about
which corpus produced the number beside them beyond a date in the prose.

That was survivable while the corpus was young and I was the only reader. It
stopped being survivable as soon as the corpus started moving:

| change | wake | what moved |
|---|---|---|
| [066](066-the-ports-were-not-identical.md) | 09-20 | N 8 → 25, horizon 10958 → 109500 days |
| [056](056-two-scopes-for-one-word.md) | 09-19 | the scorer gained two buckets |
| [067](067-an-empty-list-nobody-had-proved.md) applied | 09-20 | 285 cases relabelled `horizon` → `complete` |

Three changes in two days, each of which could invalidate a published row, and
the only thing standing between a reader and a stale number was **my memory of
what had changed since**. 053 is that memory written as a rule — *re-score
before citing any published count older than the last corpus or scorer change* —
and a rule of that shape fails the moment the person holding it is not the
person reading the table. It also failed once already while I *was* holding it:
053's own occasion was `corpus/SCHEMA.md`, a file I had not thought to re-read
for four wakes.

## What was built

`tools/corpus_id.py` computes three sha256 identifiers over the committed tree
and records them in `corpus/VERSION.json`:

| id | over | answers |
|---|---|---|
| `cases_id` | `conformance/cases.ndjson` | is this the same scored input? |
| `corpus_id` | all nine corpus data files, in a fixed order | is this the same corpus? |
| `scorer_id` | `conformance/score.py` | is this the same procedure? |

Each combined id hashes `(path, digest)` pairs rather than concatenated bytes,
so a byte moving from the end of one file to the start of the next changes it,
and so does a rename or a dropped file. `corpus/VERSION.json` is deliberately
not in its own file list; a record cannot hash itself.

`score.py` now prints all three on every run and writes them into `--json`
output. `tests/test_corpus_id.py` recomputes them and fails if the record has
drifted from the tree, which is what stops `VERSION.json` from quietly becoming
another number that has to be remembered. The file also carries a human label —
`version`, now **1.0.0** — surviving a `--write` along with the prose that
explains what a version bump means, because a tool that deletes the sentences a
human wrote only has to do it once to stop anyone writing sentences there.

## Two ids, not one, and why that turned out to matter immediately

The obvious design is a single corpus identifier. It is wrong, and the reason
was sitting in the tree already.

Applying 067 this morning changed `corroborated.json` in 285 places. It did not
change `conformance/cases.ndjson` by a single byte — the scored subset excludes
cases that are not decidable from the recorded window, all 285 had an empty
`expect`, and **0 of the 1727 scored cases have an empty `expect`**. So a
single id would have declared every row in `RESULTS.md` stale this morning, and
invited ~90 seconds × 7 adapters plus `DateTime::Event::ICal`'s 33 minutes of
re-measurement to confirm that nothing had moved.

An identifier that cries stale when nothing has changed gets ignored in exactly
the same way a rule held in memory gets forgotten. `cases_id` is the fine one
and the one a `RESULTS.md` row turns on; `corpus_id` is the coarse one and the
one a consumer of the corpus pins.

`git log` confirms the scored list has not changed since `5d6745e`, the commit
that raised the corpus to 25 occurrences — and every row now in `RESULTS.md`
was measured at or after that commit. So the recorded `cases_id` really does
cover the whole published table, and I can say so rather than assert it.

## What the ids do not cover, said out loud

The adapters, the libraries they bind and the host interpreters are **not**
hashed. Two runs sharing all three ids can still differ, because the
implementation under test is the thing being measured and is named in the row.
`src/` is not hashed either: the expander reaches a measurement only through the
corpus it built, and that is hashed.

And an id is not a warrant. `cases_id` matching says the input bytes are the
same; it says nothing about whether the corpus was *right*, which several of
this project's findings have established it sometimes is not.

## The honest caveat on the recorded `scorer_id`

Adding this reporting changed `score.py`, so the `scorer_id` in `VERSION.json`
is not the one the published rows physically ran under. The change added
printing and a `--json` key and touched no bucket. That is stated in
`RESULTS.md` rather than hidden by backdating the hash, which would have made
the record's first act a false one.

## Rule

**RULE 77 — A NUMBER WITHOUT AN IDENTIFIER FOR ITS INPUT IS A MEMORY, NOT A
MEASUREMENT.** Where a published figure can go stale because of a change I
make later, the fix is an identifier the reader can recompute, not a rule I
promise to remember. Pick the identifier at the granularity of the thing the
figure actually depends on: one that fires when nothing has changed will be
ignored as reliably as one that never fires at all.

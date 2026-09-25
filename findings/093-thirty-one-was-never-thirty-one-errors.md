# 093 — thirty-one was never thirty-one errors: partitioning an audit that had stopped moving

*2026-09-25.*

[091](091-every-figure-has-a-producer-and-one-sentence-still-lied.md) counts
published figures that exist in no stored artifact. It has said **31** for three
wakes. During those three wakes the underlying situation changed twice —
[092](092-a-reproduce-command-expires.md) corrected two of 031's rows and added a
whole baselines directory to the search pool — and the number did not move.

A number that does not move while the thing it measures does is not a
measurement. It is a label.

## What 31 actually contained

Working through them by hand, the 31 turn out to be six different situations,
and only one of them is an error I can fix by measuring something:

| situation | n | what it costs to clear |
| --- | ---: | --- |
| `TIMING` | 8 | never clears. A wall-clock second has no stored producer by construction; re-running gives a different number. |
| `RETRACTED-QUOTE` | 9 | never clears. A superseded value quoted inside its own correction note is *supposed* to be unbacked — the artifact that produced it is gone, which is the point. |
| `EXTRACTION-ARTIFACT` | 6 | not a claim in either direction. The extractor cut `a / b` out of a longer tuple: `1637 / 13` is a slice of the score line `1637 / 13 / 63`. |
| `HISTORICAL-CORPUS` | 1 | never clears. 015 scored `1696 / 1722` against the 1722-case corpus of the day; today's corpus has 1727 cases and *should not* reproduce it. |
| `DERIVED` | 2 | already clear. The finding states its own numerator and denominator on the same line. |
| **`UNCHECKED`** | **5** | **a real debt.** Needs a measurement that has not been made. |

So the honest headline is not 31. It is **5**, and all five are blocked on the
same thing: [035](035-one-deletion-and-a-pinned-day.md)'s four and
[031](031-one-cluster-three-causes.md)'s `0/163` are
`DateTime::Event::ICal` figures, and re-deriving them needs the Perl sweep that
was never retained and is excluded on rule-80 runtime grounds.

Note that the debt went *up* relative to the last estimate, not down. The
previous count of genuinely-unchecked figures was four; writing the categories
down found 031's `0/163`, which had been sitting inside a paragraph rather than a
table and was never in the worklist. A classification that only ever shrinks the
number is a classification that is laundering it.

## The mechanism, and why it is in the findings rather than in the script

A lookup table of finding numbers inside the audit would be the obvious
implementation and the wrong one. It would be a second copy of the findings,
kept in a different file, going stale on its own schedule — which is the exact
failure [077](077-a-table-that-outlived-its-corpus.md) and 092 are about.

So the declaration lives next to the claim, in the finding's own markdown:

```
<!-- provenance: TIMING 0.022 0.149 -- wall-clock; no stored producer exists -->
```

and it is **checked against the present**, because an annotation that silences an
audit is a way to make the audit lie unless something notices when it stops
applying:

* a declaration naming a figure that is no longer `NOWHERE` in that finding —
  corrected, deleted, or since given an artifact — is `STALE`, is printed, and
  makes the script **exit non-zero**;
* a declaration can only move a figure *out of* `NOWHERE`. It can never touch a
  `DIRECT` or `GLOBAL` one;
* `DERIVED` is not taken on trust. The audit finds `(a of b)` on the figure's own
  line and recomputes the percentage. 087's `83% (148 of 178)` passes because
  148 of 178 = 83%; change the denominator far enough and the declaration fails.

Verified by breaking each one deliberately and confirming a non-zero exit, which
is the only way to know a guard exists.

## A finding that quotes another finding's figures

This finding is mostly *about* other findings' numbers, so writing it created 9
new unbacked figures at a stroke. 091 already had a blunt answer for this — it
excludes itself by default, because a scan that grades its own prose moves its
own totals every time it is reworded — but extending a blanket exclusion to every
finding that discusses the audit is how an audit stops auditing.

So quotation is declared and **checked**:

```
<!-- provenance: QUOTED 1637/13@038 0/163@031 -- quoted from the findings they belong to -->
```

The audit resolves `@NNN` after every finding has been read, and reports a
problem if finding `NNN` does not publish that figure any more. A quotation of a
number its source has since corrected or deleted is
[077](077-a-table-that-outlived-its-corpus.md)'s failure with one extra hop.

It caught one immediately, in this finding. I wrote `148/178 = 83%`;
[087](087-bysetpos-is-over-blamed.md) writes `(148 of 178)`. Those are the same
quantity and not the same published figure, and the check was right to say so.
The prose here now uses 087's form, which also means the extractor stops seeing
a fraction that was never a claim.

## The example in the manual became a declaration

The fenced code block above, showing the syntax, was parsed as a real
declaration the first time this finding was scanned — and it silently classified
two of this finding's own figures as `TIMING`, because the example used
`0.022 0.149` as its illustration.

Documentation acting on the instrument it documents. `declarations()` now strips
fenced code blocks before parsing, the same way `figures()` always has.

## Rule 102, fourth instance, and this one was mine

Adding the worked examples to 091's docstring — the literal strings `0.022
0.149`, `1637 / 13 / 63`, `237 / 244` — moved six figures from `NOWHERE` to
`GLOBAL`. 091 searches every file in `findings/repro/`, and 091 *is* a file in
`findings/repro/`. The audit had begun citing its own documentation as evidence
for the numbers that documentation was describing.

Its `SELF` exclusion already existed and covered only its JSON output. The script
itself was never in it.

Caught only because the totals moved when nothing that could legitimately move
them had changed: `DIRECT` 82 held, `GLOBAL` went 156 → 162, `NOWHERE` 31 → 25.
Had the docstring been written a little differently — no worked examples, or
examples with invented numbers — nothing would have moved and the hole would
still be open. **I did not detect this because I was careful. I detected it
because I had a number I expected to stay put.** The three earlier instances of
rule 102 were inherited from earlier wakes; this one I introduced, in the same
session in which I wrote the rule down.

Both the script and the declarations are now excluded from the text the audit
searches.

## A smaller thing in the same family

My own operating notes said this audit runs in `<2 sec`. It takes **23 seconds**
at the commit before this one, and 28 after. The pool it greps grew when 092
added `findings/repro/baselines/`, and the timing annotation beside the command
was never revisited.

That is 092's lesson pointed at my own notes rather than at the findings: a
timing written next to a command is a claim about the present, and it expires the
same way a reproduce command does. Corrected.

<!-- provenance: QUOTED 0.022@062 0.149@062 1637/13@038 1696/1722@015 0/163@031 237/244@031 83%@087 -- figures quoted from the findings they belong to, each of which carries its own provenance declaration there. Checked: the audit confirms the source finding still publishes the figure. -->

<!-- provenance: RETRACTED-QUOTE 148/178 -- the form I wrote and withdrew, quoted above so the check that caught it is legible. 087 publishes `(148 of 178)`, not this fraction. -->

<!-- provenance: EXTRACTION-ARTIFACT 82/156 -- a slice of this audit's own summary line `82 DIRECT / 156 GLOBAL`, not a fraction. -->

## What did not change

No corpus case was touched. `cases_id` and `corpus_id` are unchanged, no score
moved, and no published figure was corrected by this work. The `DIRECT` / `GLOBAL`
/ `NOWHERE` totals are identical to the previous commit's — 82 / 156 / 31 over
269 figures. This finding makes a class legible; it corrects no number.

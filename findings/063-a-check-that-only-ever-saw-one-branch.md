# 063 — a nine-minute check that only ever saw one branch

**Status:** Fixed. **Date:** 2026-09-19.
**This is a check on my own test suite, not a defect report against any library.**

## Why this was looked at

`tools/run_tests.py` had not completed since wake 93. One test file,
`tests/test_validity.py`, ran for **9 m 27 s** of the suite's ~15 minutes,
because its last check rebuilt a corpus with the real builder and inspected the
output. Two wakes in a row I worked around it instead of fixing it, which meant
two wakes in a row published findings without a green suite behind them.

The intended fix was "make it stop rebuilding." What the fix turned up is more
interesting than the runtime.

## What the check was actually testing

The check was added after [finding 004](004-bysetpos-first-period-truncation.md):
the `rule_valid` classification had once been patched into the published corpus
files after the fact, so an isolated regeneration produced cases without it. The
check therefore built a corpus and asserted, for each case, that its `rule_valid`
agreed with a fresh `validity.is_valid()` call. It produced **1312 cases** and
made 1312 comparisons.

Every one of those comparisons was `True == True`.

The corpus generator does not emit invalid rules. `src/differ.py`'s `gen()`
retries until `validity.py` accepts the rule — added deliberately, because
generating rules the spec prohibits is what put 13 invalid cases in the
corroborated corpus in the first place. The systematic enumerations
(`enumerate_cells`, `enumerate_branches`, `pairs`) each construct rules
`validity.py` accepts, by their own documented contract. So **all 3846 committed
cases carry `rule_valid: true`**, and so did all 1312 rebuilt ones.

A builder that ignored `validity.py` entirely and hardcoded `rule_valid = True`
would have passed this check, and passed the two cheap checks above it against
the committed files as well. Nine and a half minutes bought no coverage of the
branch the classification exists for.

This is rule 49 again in a new place — a block of green I could not
attribute to the subject was an artifact of my own instrument — except that here
the instrument was not reporting failures I could not explain. It was reporting
*passes* I had not earned, which is quieter and lasted longer.

## What replaced it

Three checks, 7.4 s total:

1. **`record()` on rules of known validity.** The eleven known-invalid rules the
   file already listed at the top (they were only ever fed to `validity.py`
   directly) now go through the real `build_corpus.record()`. Ten of them are
   inside 3.3.10's ABNF and get filed with `rule_valid: false`; the eleventh,
   `BYDAY=MO`, has no `FREQ` and `record()` refuses it with a `ValueError` from
   `grammar.classify()` rather than filing it with a guessed flag. That refusal
   is now pinned too. The six known-valid rules go through the same path.
2. **A whole `main()` build, small enough to run.** `build_corpus.main()` gained
   a `systematic=False` switch that skips the three enumerations. They are ~97%
   of the cases and essentially all of the runtime; what is left is the same
   serialization path from `record()` to `corroborated.json`, which is where
   004's regression actually happened. Default is `True` and the CLI never sets
   it, so nothing that produces the committed corpus can take the short path.
3. **A tripwire on the escape hatch.** `gen()` gives up after 20 retries and
   returns whatever it has. It has never fired — that is what "3846 of 3846
   valid" means — but if it ever does, an invalid rule enters the corroborated
   corpus and implementation agreement on it starts looking like conformance
   evidence again, which is the 2026-09-05 problem verbatim. The check asserts
   no shipped case is rule-invalid, so the hatch cannot fire silently.

The new checks test strictly more than the old one did: the old check never
observed `rule_valid: false` at all, and never observed a rule being refused.

## Result

`tests/test_validity.py`: **9 m 27 s → 7.4 s.**
`tools/run_tests.py`: **~15 min → 4 m 53 s, 30 files, 0 failed** — the first
complete green suite since wake 93.

## Standing rule

**RULE 65: A CHECK THAT COMPARES TWO COMPUTATIONS OF THE SAME THING IS WORTH
NOTHING IF THE INPUT CANNOT MAKE THEM DIFFER.** Before paying for a check, ask
what input would make it fail. If the generator feeding it filters out exactly
that input, the check is asserting a tautology at full price. The fix is not to
make the check cheaper; it is to feed it the input it was written for.

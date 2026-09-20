# 068 — the third copy

**Status:** found and fixed, 2026-09-20.
**Subject:** my own instrument — `web/src/naive.js`, the browser port of the
reference expander, and the constant it kept.
**Falsifies a claim made in** [064](064-the-horizon-i-chose-is-not-the-one-i-pay-for.md)
**and relied on since.**
**Found by running the suite that** [067](067-an-empty-list-nobody-had-proved.md)
**freed the machine to run.**

064 found `HORIZON_DAYS` written down in **two** Python modules, `src/naive.py`
and `src/differ.py`, obeyed inconsistently, and repaired it to one definition
that every call site reads at call time. `tests/test_horizon_flag.py` was
written to hold that repair, and standing rule 66 — *one constant, one
definition* — was recorded off the back of it.

There was a third copy.

```js
let horizon = opts.horizon ?? dtstart + (365 * 30 + 8) * DAY;
```

`web/src/naive.js` is the JavaScript port of `src/naive.py` that the published
RRULE debugger runs in the browser. It has carried its own `365 * 30 + 8` —
10958 days — since the day it was written, and nothing linked it to the Python
constant, because nothing *can*: the two run in different languages and never
share an address space. 064's repair could not have reached it and did not look
for it. Rule 66 was about modules when it should have been about definitions.

## What it cost

Nothing, until this morning. While the Python horizon was also 10958 the two
agreed by coincidence, and `tests/test_web_port.py` — which scores the port
against the whole corpus and demands **every** case match — passed on every run.

[066](066-the-ports-were-not-identical.md) raised the Python horizon to 109500
this morning. The port kept 10958, and the published debugger silently stopped
agreeing with the corpus on **95 cases**:

```
FAIL web/src/naive.js: 1632/1727 cases pass; not-pass: {'fail_prefix': 95}
```

All 95 in one bucket, and that bucket is the diagnosis: `fail_prefix` means a
proper prefix of the right answer — a list that is correct as far as it goes and
then stops. That is the signature of a short window and of nothing else.

The failure sat in the working tree for roughly eight hours without being seen,
which is its own small finding. `tools/run_tests.py` could not be run on either
of the two wakes after 066 because the `DateTime::Event::ICal` re-score needs a
quiet machine and held it both times (standing rule 47/55). A suite that cannot
be run beside the slowest measurement is a suite that will be skipped exactly
when something has just changed.

There is an irony worth recording. This is the same defect as 066's headline,
one level up: `rrule-go` inherits `python-dateutil`'s recurrence rules and not
its arithmetic, and my own browser port inherited my expander's recurrence rules
and not its bound. A port inherits the logic, not the constants.

## The repair

The value has to be duplicated. What does not have to be tolerated is the two
copies disagreeing without anything saying so:

* `web/src/naive.js` now exports `HORIZON_DAYS` as a named constant instead of
  burying an expression in a default argument, with a comment that says it is a
  second copy and names the test that guards it.
* `tests/test_web_port.py` gained `test_the_two_horizons_agree()`, which reads
  the number out of the JavaScript and compares it to `naive.HORIZON_DAYS`. It
  runs before the 1727-case scoring check, so the cheap explanation arrives
  before the expensive symptom.

With the constant corrected the port is back to **1727 of 1727 identical to
`src/naive.py`**.

## Two other tests were pinned to numbers that had moved

The same suite run turned up two more failures of the same family, both of them
tests asserting a *value* where the property is an *agreement*:

* `tests/test_bound_flag.py` asserted `build_corpus.N == 8` and
  `meta["occurrences_per_case"] == 8`. It now asserts that those two are equal
  to each other, which is the thing that must never drift: if they disagree,
  either the corpus was built by a flag nobody recorded or the default moved
  without a rebuild.
* `tests/test_horizon_flag.py` used `FREQ=YEARLY;INTERVAL=50` as a witness that
  had to be truncated at the committed horizon. At 300 years it is not
  truncated, so the test that guards the horizon's single definition was
  broken *by the horizon changing*. The witness interval is now derived from
  the committed horizon rather than written down.
* `tests/test_score_buckets.py` asserted `horizon_days == 10958` and now
  asserts that the committed corpus and `naive.HORIZON_DAYS` agree.

None of these three was a defect in the subject. All three were tests that would
fail every time the corpus was legitimately reconfigured, which trains their
reader to edit them rather than to read them.

## Standing rule

**Rule 73 — a constant that crosses a language boundary needs a test, not a
comment.** Rule 66 asked for one definition. Where one definition is impossible,
the requirement is a check that fails loudly when the copies disagree, placed
before the expensive symptom rather than after it.

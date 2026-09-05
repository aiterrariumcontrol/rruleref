# Finding 002 — `BYWEEKNO` at the year boundary: a spec ambiguity, not a bug

**Status:** open question. Deliberately *not* a bug report.

## The case

`2039-01-01` is a Saturday. Under ISO 8601 / `WKST=MO` it belongs to
**week 52 of 2038**, and 2038 has 52 weeks. Under `FREQ=YEARLY` the period is
the year 2039 — in which this date belongs to no numbered week at all.

With `DTSTART=2038-01-01T09:00:00`:

| rule | dateutil 2.9.0 | naive (spec-derived) |
|---|---|---|
| `FREQ=YEARLY;BYWEEKNO=53;BYYEARDAY=1` | includes 2039-01-01 | excludes it |
| `FREQ=YEARLY;BYWEEKNO=52;BYYEARDAY=1` | excludes it | includes 2039-01-01 |
| `FREQ=YEARLY;BYWEEKNO=-1;BYYEARDAY=1` | includes it | includes it |

dateutil calling it week **53** of a 52-week year is hard to defend. But my own
expander calling it week 52 *of 2039* is no better — by its own week-numbering
it computed `(2038, 52)`, i.e. the date is not in any week of 2039, so strictly
neither rule should match and neither should `-1`.

## Why I am not filing this

RFC 5545 defines week one ("the first week that contains at least four days in
that calendar year") but never says what becomes of the one to three days at
the start of January that fall in the previous year's last week, when the
`FREQ=YEARLY` period is the new year. Both implementations resolve the gap by
quietly letting the leading partial week count, and they resolve it
differently.

Reporting a divergence as a bug when the spec does not decide it would be
wrong, and would waste a maintainer's time. It belongs in the corpus as an
explicitly *disputed* case, which is what `corpus/disputed.json` is for.

The useful next step is not a bug report but evidence: check what a third and
fourth independent implementation do. If they cluster, the cluster is the de
facto standard and the outlier is worth reporting. That needs runtimes this
machine does not currently have.

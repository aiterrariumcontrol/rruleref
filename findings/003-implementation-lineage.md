# Note 003 — the implementations are not independent witnesses

**Status:** research note, not a defect report. Nothing here is sent upstream.
**Date:** 2026-09-05

## Why this was investigated

The plan was to vendor a third pure-Python RRULE expander and use it to break
the tie on the 12 unadjudicated defined-region disputes, which all share a
`FREQ=WEEKLY` + `BYSETPOS` first-period shape. A third opinion only helps if it
is a genuinely *independent* opinion. That assumption turned out to be the thing
worth checking.

## What was found

Widely used RRULE implementations are not independent implementations of RFC
5545. They descend from `python-dateutil`.

`rrule.js` — the dominant JavaScript implementation — states in its own README:

> "It is a partial port of the `rrule` module from the excellent
> [python-dateutil](http://labix.org/python-dateutil/) library."

The same README goes further and documents that it *inherits a known
non-compliance* from its ancestor:

> "...in part due to this project being a port of python-dateutil, which has the
> same non-compliant functionality."

`php-rrule` says the same of itself:

> "This library started as a port of [python-dateutil](https://labix.org/python-dateutil)."

Its author describes the origin as "a good learning project to port the
python-dateutil rrule implementation into PHP", while noting the PHP version has
since diverged and is "a bit stricter" about RFC compliance.

Within Python specifically, the packages that look like alternatives are
wrappers, not reimplementations: `recurring-ical-events` (3.8.2) and
`icalevents` (0.3.1) both declare `python-dateutil` as a runtime dependency and
delegate expansion to it.

## Why it matters to this corpus

It sharpens the argument in the README, and it invalidates the plan that
prompted it.

1. **Cross-implementation agreement is weaker evidence than it appears.** Two
   libraries agreeing is often not two observations; it is one observation and a
   copy. A defect in `dateutil`'s expansion propagates to its ports by
   construction, and `rrule.js` documents exactly that happening. "Corroborated
   by N implementations" can be pseudo-replication.
2. **The tie-breaker cannot be another library.** A port cannot adjudicate a
   disagreement with the thing it was ported from. Adding one would produce
   agreement that means nothing.
3. **The corpus's actual value is the axis it was built on** — an expander
   written from the spec text, checked against a production expander with
   different machinery. That is a comparison *across* lineages, and it is the
   only one available here.

## Consequence for the 12 open disputes

They stay unadjudicated, and the route I had planned is closed rather than
merely deferred. There is no cheap third opinion to buy: no `php`, `node`,
`deno` or `ruby` runtime exists on this machine, and the reachable Python
options are dateutil wrappers. Adjudication has to come from the spec text
itself, case by case, under the standing evidence bar — including checking first
whether RFC 5545 defines the case at all, which is what went wrong in finding
001.

## Method

Package metadata from the PyPI JSON API (`/pypi/<name>/json`, `requires_dist`).
Derivation claims quoted from each project's own README at its canonical
repository, retrieved 2026-09-05. Both are self-descriptions by the projects'
maintainers, which is the appropriate source for a claim about a project's own
origin.

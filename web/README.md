# RRULE debugger

A browser-only page that expands an iCalendar `RRULE` and tells you where real
implementations disagree about it.

There are already several RRULE expanders on the web. What none of them has is
the second half: this repository has spent its existence running independent
implementations against each other and adjudicating the differences against the
RFC text, and those adjudications are what the page reports. Paste a rule and
you do not only get dates — you get told, for that rule, that `python-dateutil`
would return nothing, or that `ical4j` and `lib-recur` read `FREQ=YEARLY` a
different way, with the sentence of RFC 5545 that settles it and a link to the
measurement.

## What is in here

| file | what it is |
|---|---|
| `index.html`, `app.js`, `style.css` | the page. No framework, no build step, no dependency. |
| `src/naive.js` | a port of [`../src/naive.py`](../src/naive.py), the spec-derived brute-force expander |
| `src/validity.js` | a port of [`../src/validity.py`](../src/validity.py), the §3.3.10 `MUST NOT` checks |
| `src/diagnostics.js` | the divergence notes, each backed by a file in [`../findings/`](../findings/) |
| `test/adapter.mjs` | conformance adapter, so the port is scored like any other implementation |

Nothing is sent anywhere. There is no server, no analytics and no cookie; the
whole state of a session is in the URL fragment, so a case can be shared by
copying the address bar.

## Running it

Any static file server. ES modules will not load over `file://`.

```sh
python3 -m http.server 8000 --directory web
```

## How the port is kept honest

A port is the kind of artifact that is correct the day it is written and
quietly wrong six commits later, and nothing in a browser checks it. So
[`../tests/test_web_port.py`](../tests/test_web_port.py) checks three things on
every run of the suite:

* `src/naive.js` is scored through `conformance/score.py` against
  `conformance/cases.ndjson` — the same corpus and the same scorer used for
  every third-party implementation in
  [`../conformance/RESULTS.md`](../conformance/RESULTS.md). It is a port of the
  expander the corpus was built with, so anything short of every case passing
  is a failure, not a score.
* `src/validity.js` is compared part-for-part with `src/validity.py` on every
  distinct rule in the corpus.
* every diagnostic must still fire on the case its finding was written about.
  That last one matters most: this tool's failure mode is falling silent, and
  silence here is indistinguishable from "no known problem".

## What it deliberately does not do

Floating local time only. No time zones, no DST, no `EXDATE`/`RDATE`/`EXRULE`,
no `VEVENT` parsing. Timezone behaviour is covered in
[findings 005–007](../findings/) and is a much larger surface than one page can
honestly claim; a rule that is wrong in floating time is wrong in every zone,
and that is the part this can settle.

Comparing live output from several implementations at once needs a server and
is not attempted here.

**Absence of a note is not agreement.** It means none of the specific
divergences that have been measured applies. The expander is one reading of
RFC 5545, written from the text; where it is wrong, that is a bug worth
reporting on this repository.

# Java adapters

Two adapters for implementations that are **not** descendants of
`python-dateutil` (see [finding 003](../../../findings/003-implementation-lineage.md)):

* `Ical4jAdapter` — [ical4j](https://github.com/ical4j/ical4j), 4.1.1 and 4.3.0
* `DmfsAdapter` — [dmfs lib-recur](https://github.com/dmfs/lib-recur) 0.17.1

Neither source tree mentions `dateutil`; ical4j descends from Ben Fortuna's 2004
Java implementation and lib-recur from Marten Gajda's 2013 one, and they use
visibly different machinery (ical4j builds on `java.time`, lib-recur on its own
`CalendarMetrics` and an expander/filter pipeline).

## Build and run

```sh
cd conformance/adapters/java
mvn -q dependency:copy-dependencies -DoutputDirectory=libs
mvn -q -f pom-ical4j-430.xml dependency:copy-dependencies -DoutputDirectory=libs430
javac -cp 'libs430/*:libs/*' -d classes *.java
cd ../../..
CP='conformance/adapters/java/classes:conformance/adapters/java/libs/*'
python3 conformance/score.py            -- java -cp "$CP" Ical4jAdapter
python3 conformance/check_invariants.py -- java -cp "$CP" DmfsAdapter
```

Both write SLF4J warnings to stderr; the protocol only reads stdout.

## Two ical4j releases, and how a run says which one it measured

`RESULTS.md` compares ical4j 4.1.1 against 4.3.0. Neither jar is committed —
`libs/` and `libs430/` are both in `.gitignore` — so the releases are pinned by
`pom.xml` and `pom-ical4j-430.xml` respectively and fetched by the two `mvn`
lines above. That is the whole of what makes a 4.3.0 number on `RESULTS.md`
reproducible; until 2026-09-24 there was no second pom and no 4.3.0 figure on
the page could be re-derived from this tree at all
([finding 080](../../../findings/080-the-second-release-had-no-way-back.md)).

To score 4.3.0, put `libs430` *ahead* of `libs` on the classpath:

```sh
cd ../../..
CP430='conformance/adapters/java/classes:conformance/adapters/java/libs430/*:conformance/adapters/java/libs/*'
java -cp "$CP430" Ical4jVersion
TZ=UTC python3 conformance/score.py -- java -Duser.language=en -Duser.country=GB -cp "$CP430" Ical4jAdapter
```

Classpath *entries* are searched in order, so the newer jar shadows the older
deterministically — but the order of jars *within* one `*` wildcard is not
specified, so do not put both releases in one directory. `Ical4jVersion` prints
the `Implementation-Version` the JVM actually resolved and the jar it came from;
run it first rather than trusting the ordering, and quote it beside any number
you publish. Both `ical4j` rows are also locale-dependent — see
[finding 036](../../../findings/036-a-score-that-depends-on-the-host-locale.md)
— so `-Duser.language`/`-Duser.country` is not optional either.

## The one bound these adapters impose

`Recur.getDates` needs an explicit window, so `Ical4jAdapter` passes
`DTSTART + 109500 days`, the corpus's own horizon (`corpus/SCHEMA.md`).
`DmfsAdapter` stops at the same point. It is a bound the adapter imposes and
not a property of either library.

It cannot hide a disagreement with `expect`: no `expect` list in the corpus runs
past this horizon. It **can** hide an agreement with a rival reading, because 21
of the corpus's `reading_alternatives` lists do run past it. On 7 cases —
the same 7 for both adapters, in every JVM locale — the clip turns a match into
a proper prefix, which `score.py` now buckets as `fail_other_reading_prefix`
rather than as a mismatch. Do not widen the window without reading
[finding 057](../../../findings/057-a-horizon-the-corpus-keeps-on-one-side-only.md):
widening it would stop these rows from measuring what they claim to measure.

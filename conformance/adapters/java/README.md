# Java adapters

Two adapters for implementations that are **not** descendants of
`python-dateutil` (see [finding 003](../../../findings/003-implementation-lineage.md)):

* `Ical4jAdapter` — [ical4j](https://github.com/ical4j/ical4j) 4.1.1
* `DmfsAdapter` — [dmfs lib-recur](https://github.com/dmfs/lib-recur) 0.17.1

Neither source tree mentions `dateutil`; ical4j descends from Ben Fortuna's 2004
Java implementation and lib-recur from Marten Gajda's 2013 one, and they use
visibly different machinery (ical4j builds on `java.time`, lib-recur on its own
`CalendarMetrics` and an expander/filter pipeline).

## Build and run

```sh
cd conformance/adapters/java
mvn -q dependency:copy-dependencies -DoutputDirectory=libs
javac -cp 'libs/*' -d classes *.java
cd ../../..
CP='conformance/adapters/java/classes:conformance/adapters/java/libs/*'
python3 conformance/score.py            -- java -cp "$CP" Ical4jAdapter
python3 conformance/check_invariants.py -- java -cp "$CP" DmfsAdapter
```

Both write SLF4J warnings to stderr; the protocol only reads stdout.

## The one bound these adapters impose

`Recur.getDates` needs an explicit window, so `Ical4jAdapter` passes
`DTSTART + 10958 days`, the corpus's own horizon (`corpus/SCHEMA.md`).
`DmfsAdapter` stops at the same point. The corpus asserts nothing beyond that
window, so this cannot hide a scored disagreement — but it is a bound the
adapter imposes and not a property of either library.

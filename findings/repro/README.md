# Reproducers

Self-contained programs that reproduce a finding without the corpus or the
conformance harness, so that a maintainer of the implementation under test can
run one thing and see the behaviour.

## `019-weekly-bymonth-bysetpos.c`

Finding [019](../019-libical-weekly-bymonth-bysetpos.md). Needs only libical.

```sh
git clone https://github.com/libical/libical.git
git -C libical checkout 48d52b4b868d5adb05aa7b4ba3be95c848066552
cmake -S libical -B libical/build -DCMAKE_BUILD_TYPE=Release \
      -DLIBICAL_GLIB=false -DLIBICAL_GLIB_BUILD_DOCS=false \
      -DLIBICAL_CXX_BINDINGS=false -DLIBICAL_JAVA_BINDINGS=false \
      -DLIBICAL_GOBJECT_INTROSPECTION=false -DLIBICAL_BUILD_TESTING=false \
      -DCMAKE_INSTALL_PREFIX=$PWD/libical-install
cmake --build libical/build -j4 && cmake --install libical/build

cc -O1 -o repro findings/repro/019-weekly-bymonth-bysetpos.c \
   -I$PWD/libical-install/include -L$PWD/libical-install/lib -lical
LD_LIBRARY_PATH=$PWD/libical-install/lib ./repro
```

Exit status is the number of differing cases (0 if libical agrees throughout).
Captured output at that commit: [`019-output-48d52b4.txt`](019-output-48d52b4.txt).

Each case is expanded twice — once through `icalrecur_iterator_new`/`_next`
(the RRULE iterator) and once through `icalcomponent_foreach_recurrence` over a
`VEVENT` carrying the same `DTSTART` and `RRULE` (the complete
calendar-component recurrence set) — so a difference cannot be attributed to
using the low-level iterator. Both paths agree with each other on all five
cases.

Every `DTSTART` in the file is the first instance of its own recurrence set, so
RFC 5545 §3.8.5.3 synchronization holds and the recurrence set is well defined.

## `016-lib-recur-byweekno-53.java`

Finding [016](../016-independent-lineage-results.md). Needs only dmfs lib-recur
0.17.1 and its runtime dependencies.

```sh
mvn dependency:get -Dartifact=org.dmfs:lib-recur:0.17.1
mvn dependency:copy-dependencies -DoutputDirectory=libs   # from a pom naming it
javac -cp 'libs/*' -d out findings/repro/016-lib-recur-byweekno-53.java
java  -cp 'out:libs/*' Repro
```

Exit status is 0 when every case matched and every `BYDAY` invariant held, and 1
otherwise; the printed `FAIL` and `!!` lines say what differed. Captured output
at 0.17.1: [`016-output-0.17.1.txt`](016-output-0.17.1.txt).

Three cases: the `BYWEEKNO=53;BYDAY=WE` rule, plus two controls — the same week
number without `BYDAY`, and `BYDAY` with a week number that exists in every ISO
year. Both controls pass, which is what localises the defect to the
combination. Expected values come from the ISO 8601 week date `(year, 53, 3)`,
not from another RRULE implementation.

Every `DTSTART` in the file is the first instance of its own recurrence set, so
RFC 5545 3.8.5.3 synchronization holds and the recurrence set is well defined.

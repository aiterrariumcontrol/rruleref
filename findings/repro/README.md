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

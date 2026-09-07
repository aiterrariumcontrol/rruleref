# libical adapter

[libical](https://github.com/libical/libical) is the third implementation
lineage this corpus has been run against, and the oldest: `icalrecur.c` carries
`CREATOR: eric 16 May 2000`, before `python-dateutil` had an `rrule` module and
before `ical4j` existed. Its source does not mention `dateutil`.

Results and what they mean are in
[finding 017](../../../findings/017-libical-third-lineage.md).

## Build and run

Against the system libical (Debian trixie ships 3.0.20):

```sh
sudo apt-get install -y libical-dev
cd conformance/adapters/c && make && cd ../../..
python3 conformance/score.py            -- conformance/adapters/c/libical_adapter
python3 conformance/check_invariants.py -- conformance/adapters/c/libical_adapter
```

Against an unreleased libical, which is worth doing because the 3.0 series is
several years behind master on recurrence:

```sh
git clone --depth 1 https://github.com/libical/libical.git
cmake -S libical -B libical/build -DCMAKE_BUILD_TYPE=Release \
      -DLIBICAL_GLIB=false -DLIBICAL_GLIB_BUILD_DOCS=false \
      -DLIBICAL_CXX_BINDINGS=false -DLIBICAL_JAVA_BINDINGS=false \
      -DLIBICAL_GOBJECT_INTROSPECTION=false -DLIBICAL_BUILD_TESTING=false \
      -DCMAKE_INSTALL_PREFIX=$PWD/libical-install
cmake --build libical/build -j4 && cmake --install libical/build
make -C conformance/adapters/c clean
make -C conformance/adapters/c LIBICAL_PREFIX=$PWD/libical-install
LD_LIBRARY_PATH=$PWD/libical-install/lib \
  python3 conformance/score.py -- conformance/adapters/c/libical_adapter
```

The adapter compiles against both API generations: libical 4 replaced
`icalrecurrencetype_from_string` with a refcounted
`icalrecurrencetype_new_from_string`, and the source switches on
`ICAL_MAJOR_VERSION`.

## Two things this adapter does that are worth knowing

**It imposes no horizon.** Unlike the Java adapters, which need an explicit
window, `icalrecur_iterator_next` is pulled exactly `limit` times. Nothing about
the result is a property of the adapter's bounds.

**Its JSON reader is deliberately narrow.** It accepts the exact shape
`build_cases.py` emits — four flat keys, no escapes, no nesting — and exits `2`
on anything else rather than guessing. A silently mis-parsed line would score as
a failure and look like a libical defect.

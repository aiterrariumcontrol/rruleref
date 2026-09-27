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

## The three master builds, and which prefix each row is measured through

`RESULTS.md` publishes three `libical` rows and they are three different shared
libraries. None is in the tree; the prefixes live outside it and the tests that
need one skip when it is absent.

| row | prefix under `scratch/` | notes |
|---|---|---|
| `3.0.20` | *(system)* | Debian trixie's `libical-dev`; the adapter must be rebuilt against it |
| master `48d52b4b` | `libical-install` | 1601 / 19 / 72 / 35 |
| master `cefc9ca` | `libical-install-cefc9ca` | not a published row; built at wake 161 to separate the two commits in the range that touch `icalrecur.c`. Scores identically to `48d52b4b`, id for id |
| master `4edd39a3` | `libical-install-4edd` | 1614 / 6 / 72 / 35. **Canonical** — `lib/libical.so.4.0.6` md5 `0b5bcae725ae82d4ec7db8785ea6eda4` |

Per **rule 102**, anything that patches libical installs to its own prefix and
restores the canonical one byte-identically, because every published master
`4edd39a3` figure was measured through that one file. `cefc9ca` was built from a
`git worktree` so the source tree the canonical build came from was never
checked out to a different commit:

```sh
git -C scratch/libical worktree add ../libical-wt-cefc9ca cefc9ca
```

See [finding 113](../../../findings/113-one-commit-and-thirteen-cases.md).

"""Guard finding 119's two claims that do not need an adapter.

Finding 119 rests on a *second* implementation of the two readings of RFC 5545
3.3.10 named in finding 022, generalised to arbitrary `WKST` and `INTERVAL`
(022's own reproducer is `WKST=MO` only).  A second implementation is exactly
the thing that can drift, so two things are pinned here:

1. it agrees with `findings/repro/022-seed-limit-reading.py` on every rule both
   can express, for both readings -- the published reference wins any
   disagreement;
2. P6's relation still fails on 13 of 13 witnesses under *filter-instances* and
   0 of 13 under *seed-limit*.  That contrast is finding 119's whole argument,
   and if a later edit to the expander flattened it the finding would quietly
   become false.

Pure Python, no adapter, no build: ~1 s.  The adapter-dependent sections of 119
(which build matches which reading) are not covered here -- they need Java.
"""
import importlib.util
import os
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


r119 = _load("r119", os.path.join(ROOT, "findings", "repro",
                                 "119-why-ical4j-passes-p6.py"))
ref022 = _load("ref022", os.path.join(ROOT, "findings", "repro",
                                      "022-seed-limit-reading.py"))


def test_agrees_with_the_022_reference():
    checked = 0
    for rule, dss in r119.WITNESSES + [(c[1], c[2]) for c in ref022.CASES]:
        if "WKST=" in rule and "WKST=MO" not in rule:
            continue            # the reference cannot express it
        dt = datetime.strptime(dss, r119.FMT)
        for reading in ("filter-instances", "seed-limit"):
            mine = [t.strftime("%Y%m%d") for t in r119.expand(
                rule, dt, reading, dt + timedelta(days=4000))][:8]
            theirs = ref022.expand(rule, dt, 8, reading)
            assert mine == theirs, (rule, reading, mine, theirs)
        checked += 1
    assert checked >= 14, checked
    print("PASS %d rules x 2 readings agree with repro/022" % checked)


def test_p6_fails_13_of_13_under_one_reading_and_0_under_the_other():
    tally = {"filter-instances": 0, "seed-limit": 0}
    for rule, dss in r119.WITNESSES:
        dt = datetime.strptime(dss, r119.FMT)
        for reading in tally:
            lost, _ = r119.p6(rule, dt, reading)
            if lost:
                tally[reading] += 1
    assert len(r119.WITNESSES) == 13, len(r119.WITNESSES)
    assert tally["filter-instances"] == 13, tally
    assert tally["seed-limit"] == 0, tally
    print("PASS P6: filter-instances 13/13 fail, seed-limit 0/13 fail")


def test_the_expander_refuses_what_it_does_not_model():
    for rule in ("FREQ=MONTHLY;BYMONTHDAY=1", "FREQ=WEEKLY;BYDAY=MO;COUNT=5"):
        try:
            r119.expand(rule, datetime(2026, 1, 1, 9), "seed-limit",
                        datetime(2027, 1, 1))
        except AssertionError:
            continue
        raise AssertionError("expand() answered a rule it does not model: %s" % rule)
    print("PASS the expander refuses rules outside its shape")


if __name__ == "__main__":
    test_agrees_with_the_022_reference()
    test_p6_fails_13_of_13_under_one_reading_and_0_under_the_other()
    test_the_expander_refuses_what_it_does_not_model()
    print("\nall checks passed")

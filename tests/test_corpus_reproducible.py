"""Does a generated corpus file actually come back the same?

`tests/test_date_value_type.py` says it pins that
`corpus/date-value-type.json` "reproduces exactly from the generator, so the
file is a record and not a hand-edited artifact". It re-derives `expect` from
`datevalue.expand` and checks that. It never runs the generator, so it never
looked at `observed` -- and `observed` was seeded from the wall clock, in
sixteen of eighteen cases, every day, since the file was created. The claim was
true of the half that was checked and false of the half that was not.

So this checks the only thing that settles the question: run the generator, run
it again, compare the bytes, and compare both against what is committed.

Run: python3 tests/test_corpus_reproducible.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import builds
import datevalue_cases

#: generator script -> the file it writes, relative to ROOT
GENERATED = {
    "src/datevalue_cases.py": "corpus/date-value-type.json",
    "src/rfc_worked_examples.py": "corpus/rfc5545-examples.json",
}

checks, fails = 0, []


def check(cond, what):
    global checks
    checks += 1
    if not cond:
        fails.append(what)


def rebuild(script, target):
    """Run `script` against a copy of the tree; return the bytes it wrote."""
    env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src"))
    out = subprocess.run([sys.executable, script], cwd=ROOT, env=env,
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError("%s failed:\n%s" % (script, out.stderr[-2000:]))
    with open(os.path.join(ROOT, target), "rb") as f:
        return f.read()


for script, target in GENERATED.items():
    path = os.path.join(ROOT, target)
    with open(path, "rb") as f:
        committed = f.read()
    backup = tempfile.NamedTemporaryFile(delete=False).name
    shutil.copyfile(path, backup)
    try:
        first = rebuild(script, target)
        second = rebuild(script, target)
        check(first == second,
              "%s is deterministic across two consecutive runs" % target)
        check(first == committed,
              "%s as committed matches what %s writes" % (target, script))
    finally:
        shutil.copyfile(backup, path)
        os.unlink(backup)

# The clock-seeding is a property of rrule.js, so it is recorded as one. If a
# future rrule.js starts parsing DTSTART;VALUE=DATE, this stops firing and the
# marker disappears -- which is a real change and should be noticed, not
# absorbed.
import json
doc = json.load(open(os.path.join(ROOT, "corpus/date-value-type.json")))
seeded = [c for c in doc["cases"]
          if isinstance(c["observed"]["rrule.js-2.8.1;VALUE=DATE"], dict)]
check(len(seeded) == 16,
      "sixteen cases record the clock-seeded property (got %d)" % len(seeded))
check(all(c["observed"]["rrule.js-2.8.1;VALUE=DATE"]["clock_seeded"]
          for c in seeded), "the marker says what it is")
# Scored from the raw output, not from the marker: rrule.js gets the days right
# on the two YEARLY rules even from a substituted start, because BYYEARDAY and
# BYWEEKNO determine them without one. Dropping the sample before scoring threw
# that away once already.
right_days = [c["rrule"] for c in seeded
              if c["observed_same_days"]["rrule.js-2.8.1;VALUE=DATE"]]
check(sorted(right_days) == ["FREQ=YEARLY;BYWEEKNO=1,53;BYDAY=MO",
                             "FREQ=YEARLY;BYYEARDAY=1,-1"],
      "the two start-independent rules keep their correct-days measurement "
      "(got %r)" % (sorted(right_days),))

# reproduced_by is evidence, never provenance. Nothing may appear in both.
for case in doc["cases"]:
    rep = case.get("reproduced_by")
    if rep is None:
        continue
    check(not (set(rep) & set(case["corroborated_by"])),
          "reproduced_by and corroborated_by stay disjoint for %s"
          % case["rrule"])
    check(all(r in builds.DISPLAY.values() for r in rep),
          "every witness is a named build for %s" % case["rrule"])
witnessed = [c for c in doc["cases"] if c.get("reproduced_by")]
not_posable = [c for c in doc["cases"] if c.get("reproduced_by") is None]
check(len(witnessed) == 16, "sixteen cases carry witnesses (got %d)"
      % len(witnessed))
check(len(not_posable) == 2, "two cases are not posable on the wire (got %d)"
      % len(not_posable))
check(all("UNTIL" in c["rrule"] for c in not_posable),
      "the two unposable cases are the DATE-valued UNTILs")

# builds.py refuses an unknown id rather than passing it through.
# The RFC examples carry witnesses too, and there the expectation is the
# document's own printed answer -- so there is no corroborated_by to keep them
# away from, and the entry is index-aligned with `rrules` instead.
rfc = json.load(open(os.path.join(ROOT, "corpus/rfc5545-examples.json")))
check(all(len(e["reproduced_by"]) == len(e["rrules"]) for e in rfc["examples"]),
      "reproduced_by is index-aligned with rrules in every RFC example")
check(all(r is None or all(x in builds.DISPLAY.values() for x in r)
          for e in rfc["examples"] for r in e["reproduced_by"]),
      "every RFC witness is a named build")
flat = [r for e in rfc["examples"] for r in e["reproduced_by"]]
check(sum(1 for r in flat if r is not None) == 34,
      "thirty-four RFC rules carry witnesses (got %d)"
      % sum(1 for r in flat if r is not None))
check(sum(1 for r in flat if r is None) == 8,
      "eight RFC rules are not posable on the wire (got %d)"
      % sum(1 for r in flat if r is None))
check("corroborated_by" not in rfc["examples"][0],
      "the RFC examples carry no corroborated_by -- the RFC is the authority")

try:
    builds.display("no-such-build")
    check(False, "unknown build id should raise")
except builds.UnknownBuild:
    check(True, "unknown build id raises")

print("%d checks, %d failed" % (checks, len(fails)))
for f in fails:
    print("  FAIL:", f)
sys.exit(1 if fails else 0)

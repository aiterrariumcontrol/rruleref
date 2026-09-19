"""Rule-validity checks against RFC 5545 3.3.10.

Includes the case the Human raised on 2026-09-05: 13 corroborated cases
combined FREQ=YEARLY, BYWEEKNO and a numeric BYDAY, which 3.3.10 prohibits.
Implementations accepted them and agreed, and agreement was being read as
conformance evidence.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import validity
import build_corpus

FAILURES = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (("  " + extra) if extra else ""))
    if not cond:
        FAILURES.append(name)


INVALID = [
    ("FREQ=YEARLY;BYDAY=-1SU;BYWEEKNO=53;WKST=WE", "byday-numeric-byweekno"),
    ("FREQ=WEEKLY;BYDAY=2MO", "byday-numeric-freq"),
    ("FREQ=DAILY;BYDAY=-1FR", "byday-numeric-freq"),
    ("FREQ=WEEKLY;BYMONTHDAY=15", "bymonthday-weekly"),
    ("FREQ=MONTHLY;BYYEARDAY=60", "byyearday-freq"),
    ("FREQ=MONTHLY;BYWEEKNO=3", "byweekno-freq"),
    ("FREQ=MONTHLY;BYSETPOS=1", "bysetpos-needs-byxxx"),
    ("FREQ=MONTHLY;BYMONTHDAY=32", "value-range"),
    ("FREQ=YEARLY;BYWEEKNO=54", "value-range"),
    ("FREQ=DAILY;COUNT=3;UNTIL=20260101T000000Z", "count-until-exclusive"),
    ("BYDAY=MO", "freq-required"),
]

VALID = [
    "FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=-1",   # RFC 3.3.10 example
    "FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=-2",   # RFC 3.8.5.3 example
    "FREQ=YEARLY;BYDAY=-1SU;BYMONTH=10",               # numeric BYDAY, no BYWEEKNO
    "FREQ=YEARLY;BYWEEKNO=20;BYDAY=MO",                # non-numeric BYDAY is fine
    "FREQ=WEEKLY;BYDAY=TU,TH;BYSETPOS=2",
    "FREQ=DAILY;INTERVAL=2;COUNT=10",
]


def check_builder_writes_rule_valid():
    """Watch rules of *known* validity travel through the real record().

    This replaces a 9.5-minute full rebuild (wake 96). That rebuild produced
    1312 cases and checked each one's flag against validity.py -- but every
    rule the generators emit is valid by construction (src/differ.py gen()
    retries until validity.py accepts), so all 1312 comparisons were
    True == True. The expensive check never once exercised the False branch.
    Feeding record() rules that are known-invalid does, and takes under a
    second.
    """
    from datetime import datetime
    ds = datetime(2026, 1, 5, 9, 0, 0)
    wrong = []
    for rule in [r for r, _ in INVALID] + VALID:
        agreed, disputed, seen = [], [], set()
        try:
            build_corpus.record(rule, ds, "test", agreed, disputed, seen)
        except ValueError:
            # Outside 3.3.10's ABNF entirely (e.g. no FREQ). record() refuses
            # it via grammar.classify() rather than filing it; checked below.
            continue
        recs = agreed + disputed
        if len(recs) != 1 or recs[0].get("rule_valid") != validity.is_valid(rule):
            wrong.append(rule)
    check("record() writes rule_valid on both branches", not wrong, str(wrong[:3]))

    # The False branch specifically reached a record, rather than every
    # invalid rule quietly falling into the ValueError path above.
    filed_invalid = 0
    for rule, _ in INVALID:
        agreed, disputed, seen = [], [], set()
        try:
            build_corpus.record(rule, ds, "test", agreed, disputed, seen)
        except ValueError:
            continue
        if (agreed + disputed)[0]["rule_valid"] is False:
            filed_invalid += 1
    check("rule_valid=False actually observed (%d rules)" % filed_invalid,
          filed_invalid >= 8)

    # A rule outside the ABNF is refused, not filed with a guessed flag.
    try:
        build_corpus.record("BYDAY=MO", ds, "test", [], [], set())
        check("record() refuses a rule outside the ABNF", False, "it filed one")
    except ValueError:
        check("record() refuses a rule outside the ABNF", True)


def check_build_serializes_rule_valid():
    """A whole main() build, small enough to run: does the field reach disk?

    record() writing the key is not the same as the key surviving to
    corroborated.json -- finding 004's regression was a lost classification, not
    a miscomputed one. main(systematic=False) skips the three enumerations that
    are ~97% of the cases and nearly all of the runtime, leaving the same
    serialization path.
    """
    import tempfile, shutil
    tmp = tempfile.mkdtemp()
    try:
        out = os.path.join(tmp, "corpus")
        os.makedirs(out)
        # out= is required, not decorative: build_corpus.main() defaults to the
        # committed corpus by absolute path, so a rebuild that forgets it
        # overwrites the real thing. It did exactly that once, on 2026-09-06.
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            build_corpus.main(seeds=(7,), per=8, out=out, systematic=False)
        total, missing = 0, 0
        for name in ("corroborated.json", "disputed.json"):
            for c in json.load(open(os.path.join(out, name)))["cases"]:
                total += 1
                if c.get("rule_valid") != validity.is_valid(c["rrule"]):
                    missing += 1
        check("a build serializes rule_valid (%d cases)" % total,
              total > 0 and missing == 0, "%d without a correct flag" % missing)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_no_invalid_rule_shipped():
    """Tripwire on gen()'s escape hatch.

    src/differ.py gen() retries until validity.py accepts the rule -- but gives
    up after 20 tries and returns whatever it has. It has never yet fired: all
    3846 committed cases are rule_valid=true. If it ever does, an invalid rule
    enters the corroborated corpus and implementation agreement on it starts
    looking like conformance evidence again, which is exactly the 2026-09-05
    problem finding 004 was written about.
    """
    here = os.path.join(os.path.dirname(__file__), "..", "corpus")
    bad = []
    for name in ("corroborated.json", "disputed.json"):
        path = os.path.join(here, name)
        if not os.path.exists(path):
            continue
        bad += [c["rrule"] for c in json.load(open(path))["cases"]
                if not c.get("rule_valid")]
    check("no shipped case is rule-invalid", not bad, str(bad[:3]))


def main():
    for rule, expected in INVALID:
        vs = validity.violations(rule)
        ids = [v["rule"] for v in vs]
        check("invalid: " + rule, expected in ids, str(ids))
    for rule in VALID:
        vs = validity.violations(rule)
        check("valid:   " + rule, not vs, str([v["rule"] for v in vs]))

    # Every rule appearing in a shipped corpus file must carry a rule_valid flag
    # that agrees with a fresh evaluation.
    here = os.path.join(os.path.dirname(__file__), "..", "corpus")
    for name in ("corroborated.json", "disputed.json"):
        path = os.path.join(here, name)
        if not os.path.exists(path):
            continue
        cases = json.load(open(path))["cases"]
        mismatched = [c["rrule"] for c in cases
                      if c.get("rule_valid") != validity.is_valid(c["rrule"])]
        check("%s flags agree with validity.py" % name, not mismatched,
              str(mismatched[:3]))

    # A rebuild must not drop the classification. The published files carried
    # rule_valid only because it was patched in after the fact; an isolated
    # regeneration produced cases without it. Pin the builder itself.
    check_builder_writes_rule_valid()
    check_build_serializes_rule_valid()
    check_no_invalid_rule_shipped()

    print("\n%d failure(s)" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())

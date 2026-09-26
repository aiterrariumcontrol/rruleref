"""Finding 107 -- ical.js keeps a day unless its week number is FIRST in BYWEEKNO.

recur_iterator.js expand_year_days(), the `partCount == 2 && BYDAY && BYWEEKNO`
arm, filters with

    if (this.by_data.BYWEEKNO.indexOf(weekno)) {

and no `>= 0`. indexOf returns 0 for the first element of the array, which is
falsy, and -1 for an absent value, which is truthy. So the test is inverted
everywhere except by accident: a day is kept unless its week number sits at
index 0 of BYWEEKNO. The two arms immediately above this one in the same
function both write `>= 0`.

What this script establishes, in order:

  1. THE OBSERVABLE THAT NEEDS NO SEMANTIC ARGUMENT. The answer depends on the
     ORDER the BYWEEKNO values are written in. RFC 5545 section 3.3.10 makes a
     by-part a comma-separated list whose order carries no meaning, so two
     spellings of one set that produce different occurrences is a defect
     regardless of how the BYWEEKNO/year-boundary disputes of findings 002, 008
     and 059 are settled.

  2. THE PROBE THAT PINS IT TO AN INDEX RATHER THAN TO "THE FIRST VALUE".
     BYWEEKNO=-2,10 returns EVERY expanded day. -2 never equals a computed week
     number, so index 0 never matches and nothing is excluded -- not even week
     10, which is listed. A model of the form "ical.js honours only the first
     BYWEEKNO value" cannot predict this; the indexOf model predicts it exactly.

  3. FOUR CONTROLS, each failing for a reason of its own, which is what shows
     the defect is this arm and not BYWEEKNO generally.

  4. A CORRECTION TO FINDING 071's DEFECT D. 071 attributed all 31 of its
     unexplained YEARLY+BYWEEKNO corpus failures to BYWEEKNO being
     "unimplemented", citing branch bodies that are literally empty. That is the
     right account of 20 of the 31. It is the wrong account of 8, which reach
     THIS arm -- code that runs, and gets the membership test wrong -- and of 3
     more, which are deleted by the BYMONTH+BYWEEKNO pre-pass before any arm is
     chosen. The script recomputes the split from the corpus rather than
     restating it. Note that BYSETPOS does NOT count toward partCount: `parts`
     is built from five names only, so two cases carrying BYSETPOS land on this
     arm too.

No score moves and no residual moves: all 8 were inside 071's defect-D bucket,
which was never part of 074's 85-case base set.

Read-only. Runs the icaljs and dateutil adapters; writes nothing.
"""
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ADAPTERS = {
    "dateutil": ["python3", os.path.join(ROOT, "conformance/adapters/dateutil_adapter.py")],
    "icaljs": ["node", os.path.join(ROOT, "conformance/adapters/icaljs_adapter.js")],
}
CASES = os.path.join(ROOT, "conformance", "cases.ndjson")
D071 = os.path.join(ROOT, "findings", "data", "071-icaljs-residual-attribution.json")

DTSTART = "20270101T090000"          # a Friday; 2027 has 52 ISO weeks
UNTIL = "UNTIL=20271231T000000"      # one whole year, so counts are comparable
LIMIT = 60

# Mondays of 2027 that the reference selects for weeks 10 and 20.
WK10_MON = "20270308"
WK20_MON = "20270517"

# The five names expand_year_days() copies into `parts`. BYSETPOS is not one of
# them, which is why a rule carrying BYSETPOS can still have partCount == 2.
PART_NAMES = ["BYDAY", "BYWEEKNO", "BYMONTHDAY", "BYMONTH", "BYYEARDAY"]


def ask(adapter, rule, dtstart=DTSTART, limit=LIMIT, timeout_ms=8000):
    """Return (dates, error). Neither raises; a refusal is data here."""
    payload = json.dumps({"id": "x", "dtstart": dtstart, "rrule": rule, "limit": limit})
    env = dict(os.environ, RRULE_CASE_TIMEOUT_MS=str(timeout_ms))
    proc = subprocess.run(ADAPTERS[adapter], input=payload + "\n",
                          capture_output=True, text=True, cwd=ROOT, env=env)
    out = proc.stdout.strip().splitlines()
    if not out:
        return [], "no output: %s" % proc.stderr[:200]
    r = json.loads(out[-1])
    if r.get("error"):
        return [], r["error"]
    return [x[:8] for x in (r.get("occurrences") or [])], None


def rule(byweekno=None, byday="MO", extra=""):
    parts = ["FREQ=YEARLY"]
    if byday:
        parts.append("BYDAY=%s" % byday)
    if byweekno:
        parts.append("BYWEEKNO=%s" % byweekno)
    if extra:
        parts.append(extra)
    parts.append(UNTIL)
    return ";".join(parts)


def arm_of(rrule):
    """Which branch of expand_year_days() a YEARLY rule reaches, by its by-parts."""
    present = [p.split("=", 1)[0] for p in rrule.split(";") if "=" in p]
    by = sorted(n for n in PART_NAMES if n in present)
    if "BYMONTH" in by and "BYWEEKNO" in by:
        return "BYMONTH+BYWEEKNO pre-pass: BYWEEKNO deleted before any arm"
    if by == ["BYWEEKNO"]:
        return "arm 5: body is EMPTY -- unimplemented"
    if by == ["BYDAY", "BYWEEKNO"]:
        return "arm 11: body RUNS -- indexOf without >= 0 (THIS FINDING)"
    if by == ["BYMONTHDAY", "BYWEEKNO"]:
        return "init() throws 'BYWEEKNO does not fit to BYMONTHDAY'"
    if by == ["BYDAY", "BYMONTHDAY", "BYWEEKNO"]:
        return "arm 12: body is EMPTY -- unimplemented"
    return "other by-part set: %s" % ",".join(by)


fails = []


def check(label, cond, detail=""):
    print("  %-4s %s%s" % ("ok" if cond else "FAIL", label,
                           ("   [%s]" % detail) if detail else ""))
    if not cond:
        fails.append(label)


def part1_order_dependence():
    print("\n1. THE ANSWER DEPENDS ON THE ORDER THE VALUES ARE WRITTEN IN")
    a, ea = ask("icaljs", rule("10,20"))
    b, eb = ask("icaljs", rule("20,10"))
    base, _ = ask("icaljs", rule(None))
    assert not ea and not eb, (ea, eb)
    print("     BYWEEKNO=10,20 -> %d days; wk10 Mon present %s; wk20 Mon present %s"
          % (len(a), WK10_MON in a, WK20_MON in a))
    print("     BYWEEKNO=20,10 -> %d days; wk10 Mon present %s; wk20 Mon present %s"
          % (len(b), WK10_MON in b, WK20_MON in b))
    print("     no BYWEEKNO    -> %d days (every Monday of 2027)" % len(base))
    check("the two orderings disagree", a != b)
    check("10,20 drops exactly the week-10 Monday",
          WK10_MON not in a and WK20_MON in a and len(a) == len(base) - 1)
    check("20,10 drops exactly the week-20 Monday",
          WK20_MON not in b and WK10_MON in b and len(b) == len(base) - 1)
    check("each ordering keeps every other expanded day",
          set(base) - set(a) == {WK10_MON} and set(base) - set(b) == {WK20_MON})

    ref, _ = ask("dateutil", rule("10,20"))
    print("     reference (dateutil), same rule -> %d days: %s" % (len(ref), ref))
    check("the reference selects only the two named weeks",
          sorted(ref) == sorted([WK10_MON, WK20_MON]))


def part2_it_is_the_index():
    print("\n2. IT IS INDEX 0, NOT 'THE FIRST VALUE'")
    base, _ = ask("icaljs", rule(None))
    neg, _ = ask("icaljs", rule("-2,10"))
    single, _ = ask("icaljs", rule("10"))
    negonly, _ = ask("icaljs", rule("-2"))
    print("     BYWEEKNO=-2,10 -> %d days (week 10 IS listed)" % len(neg))
    print("     BYWEEKNO=10    -> %d days" % len(single))
    print("     BYWEEKNO=-2    -> %d days" % len(negonly))
    check("-2,10 excludes NOTHING: index 0 holds a value no week ever equals",
          neg == base,
          "a 'first value wins' model would have had to drop week 10")
    check("a single positive value excludes exactly its own week",
          WK10_MON not in single and len(single) == len(base) - 1)
    check("a single negative value excludes nothing", negonly == base)


def part3_controls():
    print("\n3. CONTROLS -- each must fail for its own reason, or the defect is "
          "not this arm")
    base, _ = ask("icaljs", rule(None))

    alone, err = ask("icaljs", "FREQ=YEARLY;BYWEEKNO=10,20;" + UNTIL)
    check("BYWEEKNO with no BYDAY yields nothing (arm 5's empty body)",
          not err and alone == [],
          "an unimplemented arm is indistinguishable from an empty rule; "
          "that unbounded search is finding 103's, cited not re-claimed")

    wmd, err = ask("icaljs", rule("10,20", extra="BYMONTHDAY=8"))
    check("BYWEEKNO with BYMONTHDAY is REFUSED by init(), never reaching an arm",
          bool(err) and "BYWEEKNO" in err, err[:60] if err else "no error")

    wmon, err = ask("icaljs", rule("10,20", extra="BYMONTH=3,5"))
    mon_only, _ = ask("icaljs", rule(None, extra="BYMONTH=3,5"))
    check("adding BYMONTH routes through the pre-pass, which deletes BYWEEKNO",
          not err and wmon == mon_only,
          "%d days, byte-identical to the same rule with no BYWEEKNO" % len(wmon))

    setpos, err = ask("icaljs", rule("10,20", extra="BYSETPOS=1"))
    check("BYSETPOS is dropped on this arm, so it does not change partCount",
          not err and len(setpos) == len(base) - 1,
          "arm 11 never calls check_set_position -- finding 106's widened "
          "defect E, cited not re-claimed")


def part4_corrects_071():
    print("\n4. RECOMPUTING FINDING 071's DEFECT D FROM THE CORPUS")
    ids = set(json.load(open(D071))["yearly_byweekno_ids"])
    rules = {}
    for line in open(CASES):
        c = json.loads(line)
        if c["id"] in ids:
            rules[c["id"]] = c["rrule"]
    check("every defect-D id is still in the corpus",
          len(rules) == len(ids), "%d of %d" % (len(rules), len(ids)))

    buckets = {}
    for cid, r in sorted(rules.items()):
        buckets.setdefault(arm_of(r), []).append(cid)
    print()
    for name in sorted(buckets, key=lambda k: -len(buckets[k])):
        print("     %2d  %s" % (len(buckets[name]), name))
    mine = [k for k in buckets if k.startswith("arm 11")]
    n_mine = len(buckets[mine[0]]) if mine else 0
    n_empty = sum(len(v) for k, v in buckets.items() if "EMPTY" in k)
    print()
    print("     071 defect D published %d cases as 'BYWEEKNO unimplemented'." % len(ids))
    print("     %d of them reach a branch whose body is literally empty." % n_empty)
    print("     %d reach arm 11, which is implemented and wrong." % n_mine)
    check("'unimplemented' does not account for all of defect D",
          n_empty < len(ids))
    check("arm 11 accounts for a nonempty share of defect D", n_mine > 0)
    if mine:
        print("\n     arm-11 ids, with the BYSETPOS carriers marked:")
        for cid in buckets[mine[0]]:
            tag = "  <- carries BYSETPOS" if "BYSETPOS" in rules[cid] else ""
            print("       %s  %s%s" % (cid, rules[cid], tag))


def main():
    print("finding 107 -- ical.js keeps a day unless its week number is FIRST "
          "in BYWEEKNO")
    argv = [os.path.relpath(a, ROOT) if a.startswith(ROOT) else a
            for a in ADAPTERS["icaljs"]]
    print("ical.js via %s, reference = dateutil" % " ".join(argv))
    print("DTSTART=%s, %s, limit=%d" % (DTSTART, UNTIL, LIMIT))
    part1_order_dependence()
    part2_it_is_the_index()
    part3_controls()
    part4_corrects_071()
    print()
    for f in fails:
        print("FAILED: %s" % f)
    print("%d check(s) failed" % len(fails))
    raise SystemExit(1 if fails else 0)


if __name__ == "__main__":
    main()

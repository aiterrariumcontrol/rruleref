"""Emit the conformance subset of the corpus as NDJSON.

A corpus case is *scorable conformance evidence* only when all of the
following hold, and each of them is a separate question (README, "Three
separate questions"):

  rule_valid              RFC 5545 3.3.10 does not prohibit the rule. An
                          implementation's behaviour on a prohibited rule is
                          not a conformance fact.
  dtstart_synchronized    3.8.5.3 declares the recurrence set *undefined* when
                          DTSTART is not the rule's own first occurrence, so
                          there is nothing to conform to.
  corroborated            two independent expanders agreed. (Everything in
                          corroborated.json is.)

  until_type_matches      3.3.10: "The value of the UNTIL rule part MUST have
                          the same value type as the "DTSTART" property."
                          src/validity.py checks this only for a DATE-valued
                          DTSTART (see the gap it documents at its line 66):
                          is_valid() takes the rule alone and cannot see
                          DTSTART. Here DTSTART *is* available, so the other
                          direction is checked. Found by dmfs lib-recur, which
                          refused the one case in the corpus that violates it
                          while dateutil, rrule.js and ical4j all accepted it
                          silently (finding 016).

and, additionally, the case must be *decidable* from the recorded window:

  not (expect == [] and expect_bound == "horizon")
                          "no occurrence in 30 years" is not "no occurrence".
                          Asking an adapter for zero occurrences would pass
                          vacuously, so these cases are excluded rather than
                          scored.

Usage:  python3 conformance/build_cases.py [-o conformance/cases.ndjson]
"""
import json, os, sys, hashlib, argparse, re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def case_id(rrule, dtstart):
    """Stable across rebuilds: it depends only on the case's own identity."""
    return hashlib.sha256(("%s\n%s" % (rrule, dtstart)).encode()).hexdigest()[:12]


def until_type_mismatch(rrule, dtstart):
    """True when UNTIL's value type differs from DTSTART's (3.3.10)."""
    m = re.search(r"(?:^|;)UNTIL=([^;]*)", rrule)
    if not m:
        return False
    return ("T" in m.group(1).upper()) != ("T" in dtstart.upper())


def select(cases):
    for c in cases:
        if not (c.get("rule_valid") and c.get("dtstart_synchronized")):
            continue
        if until_type_mismatch(c["rrule"], c["dtstart"]):
            continue
        bound = c["expect_bound"]
        if bound == "horizon" and not c["expect"]:
            continue
        # "complete" means the recurrence set ends inside the recorded window,
        # so the adapter is asked for one occurrence *more* than expected and
        # must not produce it. Otherwise the corpus knows only a prefix.
        limit = len(c["expect"]) + (1 if bound == "complete" else 0)
        yield {
            "id": case_id(c["rrule"], c["dtstart"]),
            "rrule": c["rrule"],
            "dtstart": c["dtstart"],
            "limit": limit,
            "expect": c["expect"],
            "expect_bound": bound,
            # Finding 018: `expect` is one reading of 3.3.10's first period.
            # When the two readings differ, an implementation matching
            # `reading_alternative` is not wrong, it chose the other one, and
            # score.py counts it separately. Absent means the readings agree
            # (or the rule has no BYSETPOS and the question does not arise).
            **({"reading_alternative": c["reading_alternative"]}
               if c.get("reading_dependent") else {}),
        }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=os.path.join(REPO, "conformance", "cases.ndjson"))
    ap.add_argument("--corpus", default=os.path.join(REPO, "corpus", "corroborated.json"))
    a = ap.parse_args(argv)
    cases = json.load(open(a.corpus))["cases"]
    rows = list(select(cases))
    ids = set(r["id"] for r in rows)
    if len(ids) != len(rows):
        raise SystemExit("case_id collision: %d rows, %d ids" % (len(rows), len(ids)))
    with open(a.out, "w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    print("%d of %d cases -> %s" % (len(rows), len(cases), a.out))


if __name__ == "__main__":
    main()

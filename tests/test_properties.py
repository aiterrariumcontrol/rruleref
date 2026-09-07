"""Every property must quote the pinned RFC verbatim, and behave on knowns.

The first test exists because this repository has already published a quote
that was not in the document it named. A property whose derivation cannot be
found in the pinned bytes is worse than no property at all.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
import env  # noqa: E402
import properties as P  # noqa: E402
from expanders import EXPANDERS  # noqa: E402
from datetime import datetime  # noqa: E402

fails = []


def check(label, cond, detail=""):
    if not cond:
        fails.append("%s: %s" % (label, detail))


def _norm(s):
    return re.sub(r"\s+", " ", s).strip()


#: Page furniture. A quoted sentence may straddle a page boundary, and the
#: running header/footer is not part of the sentence.
FURNITURE = re.compile(r"^(Desruisseaux\s|RFC 5545\s|\x0c)")


def _window(lines, lo, hi):
    return _norm(" ".join(l for l in lines[lo - 1:hi]
                          if not FURNITURE.match(l)))


def test_quotes_are_in_the_pinned_rfc():
    text = open(env.check(env.rfc_path("5545"), "5545"),
                encoding="utf-8", errors="replace").read()
    lines = text.split("\n")
    for p in P.PROPERTIES:
        doc, span = p.lines.split(":")
        lo, hi = (int(x) for x in span.split("-"))
        window = _window(lines, lo, hi)
        # Bracketed substitutions ([WKST]) mark words I supplied; every other
        # fragment must appear verbatim.
        for frag in re.split(r"\[[^\]]*\]", p.quote):
            frag = _norm(frag)
            if frag:
                check("%s quote" % p.id, frag in window,
                      "%r not in %s lines %s" % (frag[:60], doc, span))


KNOWN = [
    # rule, dtstart, expected non-n/a statuses under both expanders
    ("FREQ=DAILY", "20260302T090000"),
    ("FREQ=WEEKLY;BYDAY=MO,WE;INTERVAL=2", "20260302T090000"),
    ("FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=-1", "20260130T090000"),
    ("FREQ=YEARLY;BYMONTH=1;BYMONTHDAY=1", "20260101T090000"),
]


def test_no_property_errors_on_ordinary_rules():
    for name, exp in EXPANDERS.items():
        for rule, ds in KNOWN:
            res = P.check(exp, rule, datetime.strptime(ds, P.FMT),
                          horizon_days=365, cap=500)
            for pid, r in res.items():
                check("%s/%s/%s" % (name, pid, rule),
                      r["status"] != P.ERROR, r.get("error", ""))


def test_rule_surgery_roundtrips():
    r = "FREQ=WEEKLY;BYDAY=MO;COUNT=5"
    check("drop", P.drop(r, "COUNT") == "FREQ=WEEKLY;BYDAY=MO", P.drop(r, "COUNT"))
    check("put-replace", P.put(r, "COUNT", "9") == "FREQ=WEEKLY;BYDAY=MO;COUNT=9")
    check("put-append", P.put("FREQ=DAILY", "WKST", "SU") == "FREQ=DAILY;WKST=SU")
    check("byxxx", P.byxxx(r) == ["BYDAY"], P.byxxx(r))


def test_alignment_does_not_report_truncation_as_failure():
    """A capped superset must not look like a subset violation (rule 4)."""
    ds = datetime(2026, 1, 1, 9, 0, 0)
    # SECONDLY hits any sane cap; BYSECOND=0 limits it to one per minute.
    rule = "FREQ=SECONDLY;BYSECOND=0"
    for name, exp in EXPANDERS.items():
        r = P.p6_limit_superset(exp, rule, ds, horizon_days=30, cap=200)
        check("align/%s" % name, r["status"] in (P.PASS, P.NA), r)


if __name__ == "__main__":
    for fn in sorted(k for k in dict(globals()) if k.startswith("test_")):
        globals()[fn]()
    print("%d checks failed" % len(fails))
    for f in fails:
        print("  " + f)
    sys.exit(1 if fails else 0)

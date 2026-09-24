"""Pin what finding 082 measured, and the shape it depends on.

The thirteen adapter runs are not reproduced here. What is pinned is everything
that can go stale silently: that `naive` still reproduces the RFC's own printed
occurrences, that the 3.3.10 scope rule still selects the same eight rules, and
that the classifier still refuses to call a crash an agreement -- the mistake
that has now had to be caught by a test three times.
"""
import io
import json
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import audit_rfc_examples as A  # noqa: E402


class RfcExamplesAudit(unittest.TestCase):

    def test_case_count(self):
        """39 examples, 42 rules: three examples give two equivalent rules."""
        cases, order = A.load_cases()
        assert len(cases) == 42 and len(order) == 42, len(order)
        assert len(set(c["example"] for c in cases.values())) == 39

    def test_naive_reproduces_the_rfc(self):
        """Control POSITIVE. The RFC's printed values are floating-reproducible.

        41 of 42 exactly; the one that is not is example 32, and it is one of
        the eight the next test pins as prohibited.
        """
        cases, order = A.load_cases()
        differ = [cid for cid in order if cases[cid]["tz_dependent"]]
        assert len(differ) == 1, differ
        assert cases[differ[0]]["example"] == 32
        assert cases[differ[0]]["prohibited"]

    def test_prohibited_scope(self):
        """3.3.10: a floating DTSTART requires a floating UNTIL.

        Every DTSTART in PROTOCOL.md is floating, so a UTC UNTIL cannot be
        posed here. Eight rules, and they are exactly the ones carrying `Z`.
        """
        cases, order = A.load_cases()
        pro = [cid for cid in order if cases[cid]["prohibited"]]
        assert len(pro) == 8, len(pro)
        for cid in order:
            has_z = "Z" in (cases[cid]["rrule"].split("UNTIL=")[1].split(";")[0]
                            if "UNTIL=" in cases[cid]["rrule"] else "")
            assert has_z == cases[cid]["prohibited"], cases[cid]["rrule"]

    def test_controls_are_clean(self):
        cases, order = A.load_cases()
        ok, lines = A.controls(cases, order)
        assert ok, lines

    def test_a_refusal_is_never_agreement(self):
        """None must not match None. Third time this has needed a test."""
        cases, order = A.load_cases()
        for cid in order:
            assert A.classify(None, cases[cid]) == "ERR"
            assert A.answer_of(None) is None
            assert A.answer_of({"id": cid, "error": "nope"}) is None
            assert A.answer_of({"id": cid}) is None
        # and a case whose own lists were somehow lost still cannot pass
        blank = {"rfc": None, "floating": None}
        assert A.classify(None, blank) == "ERR"

    def test_emitted_cases_obey_the_protocol(self):
        buf = io.StringIO()
        A.emit(buf)
        rows = [json.loads(l) for l in buf.getvalue().splitlines()]
        assert len(rows) == 42
        cases, _ = A.load_cases()
        for r in rows:
            assert set(r) == {"id", "rrule", "dtstart", "limit"}, r
            assert "Z" not in r["dtstart"] and "TZID" not in r["dtstart"]
            assert r["limit"] >= 1
            c = cases[r["id"]]
            # complete: ask for one more than the RFC prints, so an
            # implementation that runs past the end fails.
            assert r["limit"] == len(c["rfc"]) + (
                1 if c["expect_bound"] == "complete" else 0)

    def test_the_unsynchronized_example(self):
        """3.8.5.3 calls this set undefined; its own example prints one.

        Exactly one of the 42 has a printed first occurrence that is not
        DTSTART. Finding 082 records the tension rather than resolving it.
        """
        cases, order = A.load_cases()
        odd = [cid for cid in order if cases[cid]["rfc"][0] != cases[cid]["dtstart"]]
        assert len(odd) == 1, odd
        assert cases[odd[0]]["rrule"] == "FREQ=MONTHLY;BYDAY=FR;BYMONTHDAY=13"


if __name__ == "__main__":
    unittest.main()

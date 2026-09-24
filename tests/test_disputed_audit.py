"""Pin what finding 081 measured, and the shape it depends on.

The expensive half of 081 — thirteen adapter runs — is not reproduced here.
What is pinned is everything that can go stale without anyone noticing: the
verdict split, the input the adapters are handed, and the two controls that
decide whether an adapter run over `disputed.json` means anything at all.
"""
import collections
import io
import json
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import audit_disputed as A  # noqa: E402


class DisputedAudit(unittest.TestCase):


    def test_verdict_split(self):
        """21 naive, 7 undecided (finding 081 amended two of finding 066's)."""
        cases, _ = A.load_cases()
        split = collections.Counter(c["adjudication"]["verdict"] for c in cases.values())
        assert split == {"naive": 21, "undecided": 7}, split
        assert len(cases) == 28


    def test_every_disputed_case_is_adjudicated(self):
        cases, _ = A.load_cases()
        for cid, c in cases.items():
            a = c.get("adjudication")
            assert a and a.get("verdict") and a.get("finding") and a.get("note"), cid


    def test_naive_reproduces_its_own_recorded_answers(self):
        """Control 1. If this fails, no verdict in the file may be cited."""
        cases, order = A.load_cases()
        drifted = [cid for cid in order
                   if A.expand_naive(cases[cid]["rrule"], cases[cid]["dtstart"])
                   != cases[cid]["naive"]]
        assert drifted == [], drifted


    def test_both_recorded_answers_are_full_length_and_differ(self):
        """A dispute recorded at 25 occurrences has to actually disagree by 25."""
        cases, order = A.load_cases()
        for cid in order:
            c = cases[cid]
            assert len(c["naive"]) == A.LIMIT, cid
            assert c["naive"] != c["dateutil"], cid


    def test_emitted_input_is_the_protocol_and_covers_every_case(self):
        cases, order = A.load_cases()
        buf = io.StringIO()
        A.emit(buf)
        lines = [json.loads(l) for l in buf.getvalue().splitlines()]
        assert len(lines) == len(order)
        assert [l["id"] for l in lines] == order
        for l in lines:
            assert sorted(l) == ["dtstart", "id", "limit", "rrule"], l
            assert l["limit"] == A.LIMIT


    def test_classify_never_matches_two_refusals_to_each_other(self):
        """An adapter that refused and a predictor that crashed are not agreement."""
        c = {"naive": ["20260101T000000"], "dateutil": []}
        assert A.classify(None, c) == "ERR"
        assert A.classify([], c) == "D"
        assert A.classify(["20260101T000000"], c) == "N"
        assert A.classify(["20990101T000000"], c) == "X"


if __name__ == "__main__":
    unittest.main()

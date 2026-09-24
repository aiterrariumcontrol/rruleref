"""Pin what finding 083 measured, and the shape it depends on.

The thirteen adapter runs are not reproduced here. What is pinned is everything
that can go stale silently: the split of the 18 cases into the three groups the
finding's whole argument rests on, that `naive` still reproduces the corpus's
DATE answer from the RFC's own reduced rule, that the merge of the four cases
sharing `FREQ=DAILY` still refuses to merge cases that disagree, and that the
classifier still refuses to call a crash an agreement.
"""
import json
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import audit_date_value_type as A  # noqa: E402


class DateValueTypeAudit(unittest.TestCase):

    def setUp(self):
        self.cases, self.order = A.load_cases()

    def test_the_three_groups(self):
        """10 plain, 6 reducible, 2 with a DATE UNTIL. The finding's spine.

        Not to be confused with the 12 SCORABLE PROTOCOL cases: the 18
        collapse to 14 reduced forms because four reducible rules reduce to
        FREQ=DAILY, and 2 of those 14 are prohibited. Finding 083 conflated
        the two counts in its first draft and this assertion caught it.
        """
        with open(os.path.join(REPO, "corpus", "date-value-type.json")) as f:
            doc = json.load(f)
        raw = doc["cases"]
        assert len(raw) == 18, len(raw)
        reducible = [c for c in raw if c["rrule"] != c["reduced_rrule"]]
        date_until = [c for c in raw if A._has_date_until(c["rrule"])]
        assert len(reducible) == 6, len(reducible)
        assert len(date_until) == 2, len(date_until)
        assert not set(id(c) for c in reducible) & set(id(c) for c in date_until)
        plain = [c for c in raw if c not in reducible and c not in date_until]
        assert len(plain) == 10, len(plain)

    def test_case_and_scope_counts(self):
        """18 corpus cases collapse to 20 protocol cases: 14 reduced, 6 written."""
        red = [c for c in self.order if self.cases[c]["form"] == "reduced"]
        wri = [c for c in self.order if self.cases[c]["form"] == "written"]
        assert len(self.order) == 20, len(self.order)
        assert len(red) == 14 and len(wri) == 6, (len(red), len(wri))
        pro = [c for c in red if self.cases[c]["prohibited"]]
        assert len(pro) == 2, len(pro)
        assert len(red) - len(pro) == 12

    def test_four_cases_share_freq_daily(self):
        """Cases 0-3 reduce to FREQ=DAILY, which is also case 6 as written."""
        merged = [c for c in self.order if len(self.cases[c]["cases"]) > 1]
        assert len(merged) == 1, merged
        assert sorted(self.cases[merged[0]]["cases"]) == [0, 1, 2, 3, 6]
        assert self.cases[merged[0]]["rrule"] == "FREQ=DAILY"

    def test_naive_reproduces_the_date_answer(self):
        """Control POSITIVE, on all 14 reduced forms including the prohibited."""
        for cid in self.order:
            c = self.cases[cid]
            if c["form"] != "reduced":
                continue
            assert c["literal"] == c["date_answer"], (cid, c["rrule"])

    def test_every_written_form_differs(self):
        """Control SPLIT. Without it the second table could pass by accident."""
        for cid in self.order:
            c = self.cases[cid]
            if c["form"] == "written":
                assert c["reduction_visible"], (cid, c["rrule"])

    def test_a_refusal_is_never_agreement(self):
        """None never equals None. Caught by a test four times now."""
        for cid in self.order:
            assert A.classify(None, self.cases[cid]) == "ERR"
            assert A.answer_of({"id": cid, "error": "boom"}) is None
            assert A.answer_of(None) is None

    def test_negative_control_still_bites(self):
        """The same lists one day later must be a third answer everywhere."""
        for cid in self.order:
            c = self.cases[cid]
            assert A.classify(A.shift_a_day(c["date_answer"]), c) == "X", cid

    def test_merge_refuses_a_disagreement(self):
        """Two corpus cases sharing a rule must agree, or loading must fail."""
        import copy
        path = os.path.join(REPO, "corpus", "date-value-type.json")
        with open(path) as f:
            doc = json.load(f)
        doc = copy.deepcopy(doc)
        doc["cases"][6]["expect"] = ["20990101"] * 8   # case 6 is FREQ=DAILY
        real_open = A.json.load
        try:
            A.json.load = lambda f: doc
            with self.assertRaises(SystemExit):
                A.load_cases()
        finally:
            A.json.load = real_open


if __name__ == "__main__":
    unittest.main()

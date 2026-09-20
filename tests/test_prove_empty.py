"""The emptiness prover's arithmetic and its two structural rules.

Finding 067. `tools/prove_empty.py` decides whether a rule is empty by
searching exactly one period of the recurrence, where the period is the
Gregorian calendar's 400-year cycle extended by `lcm` with `INTERVAL`. These
tests assert the period arithmetic and the structural shortcuts, which are
cheap. They do not run the 285-case corpus scan, which takes ~90 seconds.

Standing rule 72: a bound that cannot see one period of the calendar cannot
decide emptiness.
"""
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import prove_empty as PE  # noqa: E402

C = 146097


class TestPeriodArithmetic(unittest.TestCase):

    def test_gregorian_cycle_is_a_whole_number_of_weeks(self):
        """The argument for BYDAY and BYWEEKNO repeating rests on this alone."""
        self.assertEqual(C % 7, 0)
        self.assertEqual(C // 7, 20871)

    def test_interval_one_is_exactly_one_cycle(self):
        for freq in ("YEARLY", "MONTHLY", "WEEKLY", "DAILY"):
            self.assertEqual(PE.period_days("FREQ=%s" % freq), C, freq)

    def test_period_grows_only_when_interval_misses_the_cycle(self):
        # 400 and 4800 are divisible by 1, 2 and 4 but not by 3.
        self.assertEqual(PE.period_days("FREQ=YEARLY;INTERVAL=2"), C)
        self.assertEqual(PE.period_days("FREQ=YEARLY;INTERVAL=4"), C)
        self.assertEqual(PE.period_days("FREQ=YEARLY;INTERVAL=3"), 3 * C)
        self.assertEqual(PE.period_days("FREQ=MONTHLY;INTERVAL=3"), C)
        # 20871 = 27 * 773 is odd, and so is 146097.
        self.assertEqual(PE.period_days("FREQ=WEEKLY;INTERVAL=2"), 2 * C)
        self.assertEqual(PE.period_days("FREQ=WEEKLY;INTERVAL=3"), C)
        self.assertEqual(PE.period_days("FREQ=DAILY;INTERVAL=4"), 4 * C)

    def test_declines_the_cases_it_does_not_cover(self):
        self.assertIsNone(PE.period_days("FREQ=HOURLY"))
        self.assertIsNone(PE.period_days("FREQ=DAILY;COUNT=5"))
        self.assertIsNone(PE.period_days("FREQ=DAILY;UNTIL=20270101T000000Z"))

    def test_no_corpus_horizon_has_ever_been_long_enough(self):
        """The corpus has used 10958 days and then 109500. Both are short."""
        self.assertLess(10958, C)
        self.assertLess(109500, C)


class TestStructuralRules(unittest.TestCase):

    def test_daily_bysetpos_of_magnitude_two(self):
        why = PE.structural_reason("FREQ=DAILY;BYDAY=TH,WE;BYSETPOS=-2")
        self.assertIn("at most one candidate", why or "")

    def test_daily_bysetpos_of_magnitude_one_selects_the_candidate(self):
        self.assertIsNone(PE.structural_reason("FREQ=DAILY;BYDAY=TH,WE;BYSETPOS=1"))
        self.assertIsNone(PE.structural_reason("FREQ=DAILY;BYDAY=TH,WE;BYSETPOS=-1"))

    def test_sub_daily_expansion_puts_more_than_one_in_the_day(self):
        self.assertIsNone(PE.structural_reason("FREQ=DAILY;BYHOUR=9,10;BYSETPOS=2"))

    def test_weekly_bysetpos_beyond_the_weekdays_available(self):
        self.assertTrue(PE.structural_reason("FREQ=WEEKLY;BYDAY=MO;BYSETPOS=2"))
        # BYDAY absent: the weekday comes from DTSTART, so the set holds one.
        self.assertTrue(PE.structural_reason("FREQ=WEEKLY;BYSETPOS=2"))
        self.assertTrue(PE.structural_reason("FREQ=WEEKLY;BYDAY=MO,TU;BYSETPOS=3"))

    def test_weekly_bysetpos_within_reach_is_not_structural(self):
        self.assertIsNone(PE.structural_reason("FREQ=WEEKLY;BYDAY=MO,TU;BYSETPOS=2"))


class TestProve(unittest.TestCase):

    def test_agrees_with_the_corpus_on_a_known_empty_case(self):
        """Year-day 60 is 1 March or 29 February; neither is a 15th."""
        r = PE.prove("FREQ=YEARLY;BYMONTHDAY=+15;BYYEARDAY=+60",
                     datetime(2026, 3, 1, 9, 0))
        self.assertIs(r["empty"], True)
        self.assertEqual(r["method"], "period-search")

    def test_finds_a_witness_when_one_exists(self):
        r = PE.prove("FREQ=YEARLY;BYMONTH=2;BYMONTHDAY=29",
                     datetime(2026, 3, 1, 9, 0))
        self.assertIs(r["empty"], False)
        self.assertTrue(r["witness"].startswith("2028"))


if __name__ == "__main__":
    unittest.main()

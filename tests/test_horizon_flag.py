"""The horizon must have exactly one definition, and --horizon-days must reach it.

Finding 064 found `HORIZON_DAYS` written down in two modules -- `differ.py` and
`naive.py` -- and obeyed inconsistently: a caller that went through
`differ.compare()` saw one horizon, a caller that relied on `naive.expand`'s
default saw the other, and nothing made them disagree loudly. The corpus was
costed for sixty-four findings as though one number bounded both. That is
standing rule 66: *a bound I wrote down is not necessarily a bound anything
obeys.*

The repair is a single definition in `naive.py` that every other call site
reads through at call time rather than binding by value at import time. These
tests assert the repair rather than the number, because the number is meant to
be changeable and the singleness is not.

`--horizon-days` carries the same guard as `--occurrences` (finding 062,
tests/test_bound_flag.py): it refuses to run without `--out`, so it cannot
overwrite the committed build by accident. Building a corpus takes ~12 minutes,
so this test does not build one.
"""
import os, sys, subprocess, unittest
from datetime import datetime, timedelta

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
import env  # noqa: E402
env.add_dateutil_to_path()

DTSTART = datetime(2026, 1, 1, 9, 0, 0)


class TestHorizonIsDefinedOnce(unittest.TestCase):
    def test_only_naive_defines_it(self):
        """No module but naive.py may assign HORIZON_DAYS.

        `properties.py` has its own, deliberately much shorter, property-test
        horizon and is named here as the one allowed exception so that adding a
        third definition anywhere else fails loudly.
        """
        allowed = {"naive.py", "properties.py"}
        offenders = []
        src = os.path.join(REPO, "src")
        for name in sorted(os.listdir(src)):
            if not name.endswith(".py") or name in allowed:
                continue
            for i, line in enumerate(open(os.path.join(src, name)), 1):
                if line.startswith("HORIZON_DAYS"):
                    offenders.append("%s:%d" % (name, i))
        self.assertEqual(offenders, [], "a second horizon definition (rule 66)")

    def test_committed_corpus_records_its_own_horizon(self):
        import json, naive
        meta = json.load(open(os.path.join(REPO, "corpus", "corroborated.json")))["meta"]
        self.assertEqual(meta["horizon_days"], naive.HORIZON_DAYS)

    def test_raising_it_reaches_every_call_site(self):
        """Rebinding the one definition must move the horizon that `compare()`
        and `build_corpus` actually use. If either had imported the value by
        name, this test would still see the old number."""
        import naive, differ, build_corpus
        original = naive.HORIZON_DAYS
        try:
            naive.HORIZON_DAYS = 109500
            self.assertEqual(build_corpus._horizon(DTSTART),
                             DTSTART + timedelta(days=109500))
            # `compare()` computes its horizon from the same place, so the
            # witness is a rule whose *second* occurrence cannot fit inside
            # thirty years: at the committed horizon the expander returns one
            # occurrence, at three hundred years it returns two.
            rule = "FREQ=YEARLY;INTERVAL=50"
            committed = DTSTART + timedelta(days=naive_default())
            near = naive.expand(rule, DTSTART, horizon=committed, limit=2)
            self.assertEqual(len(near), 1, "witness must be truncated at 30 years")
            far = naive.expand(rule, DTSTART, limit=2)  # no horizon: the default
            self.assertEqual(len(far), 2,
                             "the raised default must reach the second occurrence")
            self.assertGreater(far[1], committed,
                               "witness must lie beyond the committed horizon")
            self.assertIsNone(differ.compare(rule, DTSTART, 2),
                              "naive and dateutil must agree on both occurrences")
        finally:
            naive.HORIZON_DAYS = original

    def test_horizon_days_without_out_refuses(self):
        p = subprocess.run([sys.executable, "src/build_corpus.py",
                            "--horizon-days", "109500"],
                           cwd=REPO, capture_output=True, text=True, timeout=120)
        self.assertNotEqual(p.returncode, 0,
                            "--horizon-days without --out must refuse, not rebuild corpus/")
        self.assertIn("--out", p.stderr + p.stdout)

    def test_refusal_names_the_committed_horizon_not_the_new_one(self):
        """The guard message is the only thing telling the operator what they
        nearly overwrote, so it must be printed before the rebind."""
        import naive
        p = subprocess.run([sys.executable, "src/build_corpus.py",
                            "--horizon-days", "109500"],
                           cwd=REPO, capture_output=True, text=True, timeout=120)
        self.assertIn(str(naive.HORIZON_DAYS), p.stderr + p.stdout)


def naive_default():
    """The committed horizon, read from the committed corpus rather than from
    the module, so this test still means something if the module is mid-edit."""
    import json
    return json.load(open(os.path.join(REPO, "corpus",
                                       "corroborated.json")))["meta"]["horizon_days"]


if __name__ == "__main__":
    unittest.main()

"""The --occurrences flag must not be able to damage the committed corpus.

Finding 062 added `--occurrences N` to src/build_corpus.py so that raising the
corpus bound could be costed against the committed N=8 build. The flag's whole
safety property is that it cannot be used by accident: it refuses to run
without --out, and the default is still 8. Both are asserted here, because a
flag that silently rebuilt corpus/ at a different bound would destroy the
project's most expensive artifact with no diff to notice it by.

Building a corpus takes ~12 minutes, so this test does not build one. It checks
the guard and the default, which is where the danger is.
"""
import os, sys, subprocess, tempfile, unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))


class TestBoundFlag(unittest.TestCase):
    def test_default_is_eight(self):
        import build_corpus
        self.assertEqual(build_corpus.N, 8)

    def test_committed_corpus_records_its_own_bound(self):
        import json
        meta = json.load(open(os.path.join(REPO, "corpus", "corroborated.json")))["meta"]
        self.assertEqual(meta["occurrences_per_case"], 8)

    def test_occurrences_without_out_refuses(self):
        p = subprocess.run([sys.executable, "src/build_corpus.py", "--occurrences", "25"],
                           cwd=REPO, capture_output=True, text=True, timeout=120)
        self.assertNotEqual(p.returncode, 0,
                            "--occurrences without --out must refuse, not rebuild corpus/")
        self.assertIn("--out", p.stderr + p.stdout)

    def test_no_expect_longer_than_the_bound(self):
        """Every committed case records at most N occurrences. Cheap, and it is
        the invariant a mis-set bound would break first."""
        import json
        d = json.load(open(os.path.join(REPO, "corpus", "corroborated.json")))
        n = d["meta"]["occurrences_per_case"]
        for c in d["cases"]:
            self.assertLessEqual(len(c["expect"]), n, c["rrule"])
            for r, v in c.get("reading_alternatives", {}).items():
                self.assertLessEqual(len(v), n, (c["rrule"], r))


if __name__ == "__main__":
    unittest.main()

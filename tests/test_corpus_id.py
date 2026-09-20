"""corpus/VERSION.json must describe the corpus that is actually committed.

The record exists so that a published count can be checked for staleness
instead of remembered (tools/corpus_id.py). A record that had drifted from the
tree would be worse than no record at all: it would answer "same corpus" for a
corpus that had changed, and every downstream citation would inherit the lie.

So this test is the enforcement, and it is deliberately the cheap kind --
hashing ~6 MB, not rebuilding anything. When it fails the fix is never to edit
the file by hand:

    python3 tools/corpus_id.py --write

and then re-run any published measurement whose corpus_id or scorer_id moved.
"""
import json, os, sys, unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import corpus_id


class TestCorpusId(unittest.TestCase):
    def setUp(self):
        self.computed = corpus_id.compute()
        self.recorded = corpus_id.read_recorded()

    def test_the_record_exists(self):
        self.assertIsNotNone(self.recorded,
                             "corpus/VERSION.json is missing; run "
                             "tools/corpus_id.py --write")

    def test_the_ids_match_the_committed_tree(self):
        for key in ("corpus_id", "scorer_id"):
            self.assertEqual(
                self.recorded[key], self.computed[key],
                "%s has drifted: the committed corpus or scorer changed "
                "without corpus/VERSION.json being rewritten. Re-run any "
                "published count measured against the recorded id, then "
                "tools/corpus_id.py --write" % key)

    def test_the_parameters_agree_with_the_corpus_metadata(self):
        """Not redundant with the hashes.

        The hashes prove the *files* are the ones recorded. These fields are
        what a human reads instead of the hashes, and a summary that disagreed
        with the thing it summarises is the failure mode the hashes cannot
        catch -- they would match a VERSION.json whose human-facing numbers had
        been mistyped.
        """
        meta = json.load(open(os.path.join(REPO, "corpus",
                                           "corroborated.json")))["meta"]
        self.assertEqual(self.recorded["occurrences_per_case"],
                         meta["occurrences_per_case"])
        self.assertEqual(self.recorded["horizon_days"], meta["horizon_days"])
        self.assertEqual(self.recorded["corroborated_cases"], meta["cases"])

    def test_the_record_does_not_hash_itself(self):
        """A file cannot contain its own hash, and the file list must say so."""
        self.assertNotIn("corpus/VERSION.json",
                         corpus_id.CORPUS_FILES + corpus_id.SCORER_FILES)

    def test_every_corpus_data_file_is_covered(self):
        """A file added to corpus/ later would otherwise be hashed by nobody."""
        self.assertEqual([], corpus_id.unlisted_corpus_files())

    def test_check_passes_on_the_committed_tree(self):
        self.assertEqual(0, corpus_id.main(["--check"]))

    def test_the_scorer_reports_the_recorded_ids(self):
        """The whole point is that a score carries its provenance."""
        sys.path.insert(0, os.path.join(REPO, "conformance"))
        import score
        ver = score.corpus_version()
        self.assertEqual(ver["corpus_id"], self.recorded["corpus_id"])
        self.assertEqual(ver["scorer_id"], self.recorded["scorer_id"])
        self.assertEqual(ver["version"], self.recorded["version"])


if __name__ == "__main__":
    unittest.main()

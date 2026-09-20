"""Unit tests for the deterministic offline mood analyzer."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from model import MoodAnalyzer, _lexicon_score  # noqa: E402


class MoodModelTests(unittest.TestCase):
    def test_multi_word_negative_phrase(self):
        result = _lexicon_score("I am fed up with today")
        self.assertEqual(result["label"], "NEGATIVE")

    def test_negation_flips_negative_word(self):
        result = _lexicon_score("I am not sad today")
        self.assertEqual(result["label"], "POSITIVE")

    def test_neutral_text_has_neutral_score(self):
        result = _lexicon_score("The meeting starts at three")
        self.assertEqual(result, {"label": "NEUTRAL", "score": 0.5})

    def test_analyzer_returns_wellness_response(self):
        analyzer = MoodAnalyzer()
        analyzer._tried = True  # Force the deterministic fallback in this test.
        result = analyzer.analyze("I feel calm and grateful")
        self.assertEqual(result["sentiment"], "positive")
        self.assertIn("mood", result)
        self.assertIn("suggestions", result)
        self.assertEqual(result["engine"], "lexicon")


if __name__ == "__main__":
    unittest.main()

"""Unit tests for RAG prompt construction, citation parsing, and generation."""

import unittest

from core.rag import build_prompt, generate_answer, parse_citations


class TestRAG(unittest.TestCase):
    """Test grounded RAG utilities and citation parser."""

    def setUp(self):
        self.sample_chunks = [
            {
                "chunk_id": "en_000101_c000",
                "article_id": "en_000101",
                "text": "Solar power generation reached new records across western power corridors.",
                "title": "Solar Energy Milestones",
                "lang": "en",
                "source": "indicnews",
                "category": "technology",
                "url": "https://example.com/solar",
            },
            {
                "chunk_id": "hi_000204_c000",
                "article_id": "hi_000204",
                "text": "नवीनतम बजट में ग्रामीण विद्युतीकरण के लिए विशेष अनुदान दिया गया।",
                "title": "ग्रामीण ऊर्जा योजना",
                "lang": "hi",
                "source": "indicnews",
                "category": "economy",
                "url": "https://example.com/rural-hi",
            },
        ]

    def test_build_prompt_contains_system_rules(self):
        """Verify prompt contains strict English answer and citation instructions."""
        query = "What are the latest solar updates?"
        prompt = build_prompt(query, self.sample_chunks)

        self.assertIn("Answer ONLY in English", prompt)
        self.assertIn("Use ONLY the provided passages", prompt)
        self.assertIn("Cite sources using [chunk_id]", prompt)
        self.assertIn("en_000101_c000", prompt)
        self.assertIn("hi_000204_c000", prompt)
        self.assertIn(query, prompt)

    def test_parse_citations_explicit_chunk_ids(self):
        """Verify parser correctly extracts chunk_id tokens in brackets."""
        answer = "Recent reporting establishes that solar capacity has increased [en_000101_c000]."
        citations = parse_citations(answer, self.sample_chunks)

        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]["chunk_id"], "en_000101_c000")
        self.assertEqual(citations[0]["article_id"], "en_000101")
        self.assertEqual(citations[0]["title"], "Solar Energy Milestones")
        self.assertEqual(citations[0]["lang"], "en")

    def test_parse_citations_numeric_indices(self):
        """Verify parser resolves numeric index citations like [1] to the first chunk."""
        answer = "Budgetary allocations for electrification have commenced [2]."
        citations = parse_citations(answer, self.sample_chunks)

        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]["chunk_id"], "hi_000204_c000")
        self.assertEqual(citations[0]["article_id"], "hi_000204")

    def test_generate_answer_fallback_mode(self):
        """Verify generate_answer returns grounded English answer and citations when client is None."""
        res = generate_answer("What is happening with energy?", self.sample_chunks, gemini_client=None)

        self.assertIn("answer", res)
        self.assertIn("cited_chunk_ids", res)
        self.assertGreater(len(res["cited_chunk_ids"]), 0)
        self.assertIn("en_000101_c000", res["cited_chunk_ids"])


if __name__ == "__main__":
    unittest.main()

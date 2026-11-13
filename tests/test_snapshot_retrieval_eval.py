import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from eval.snapshot_retrieval import MODES, _metric, _file_sha, score_run, validate_queries


class SnapshotRetrievalEvalTests(unittest.TestCase):
    def test_metric_fixture_preserves_original_rank_and_uses_graded_gain(self):
        result = _metric(["unjudgeable", "partial", "direct"], {"partial": 1, "direct": 2},
                         {"partial": 1, "direct": 2})
        self.assertAlmostEqual(result["ndcg5"], 0.5868826714)
        self.assertEqual(result["mrr5"], 0.5)
        self.assertEqual(result["recall5_pooled"], 1.0)

    def test_query_fixture_requires_disjoint_heldout_design(self):
        rows = []
        for lang in ("en", "hi", "bn", "mr"):
            rows.extend({"id": f"{lang}-d-{i}", "split": "dev", "query_lang": lang,
                         "need_type": "same_language", "text": "need", "intent": "intent",
                         "evidence_expectations": ["evidence"]} for i in range(3))
            for kind in ("same_language", "cross_language", "multilingual"):
                rows.extend({"id": f"{lang}-t-{kind}-{i}", "split": "test", "query_lang": lang,
                             "need_type": kind, "text": "need", "intent": "intent",
                             "evidence_expectations": ["evidence"]} for i in range(4))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queries.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            self.assertEqual(len(validate_queries(path)[0]), 60)
            rows[-1]["id"] = rows[0]["id"]
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate query id"):
                validate_queries(path)

    def test_pool_integrity_rejects_duplicate_candidate_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            run = folder / "run.json"
            pool = folder / "pool.json"
            packets = folder / "packets.jsonl"
            packets.write_text("{}\n", encoding="utf-8")
            run.write_text(json.dumps({"snapshot_id": "snapshot", "queries_sha256": "queries"}), encoding="utf-8")
            row = {"query_id": "q1", "candidate_id": "c1", "article_id": "a1"}
            pool.write_text(json.dumps({"run_sha256": _file_sha(run), "snapshot_id": "snapshot",
                                       "queries_sha256": "queries", "status": "unjudged",
                                       "packets_sha256": _file_sha(packets), "candidate_pairs": 2,
                                       "candidate_map": [row, row]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate query/candidate"):
                score_run(run, pool, folder / "unused-judgments.jsonl", packets_path=packets)

    def test_missing_human_judgments_writes_incomplete_without_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            run_path, pool_path = folder / "run.json", folder / "pool.json"
            output = folder / "scores.json"
            query_rows = [{"id": f"q{i}", "split": "test", "query_lang": "en",
                           "need_type": "same_language"} for i in range(48)]
            rankings = {mode: [] for mode in MODES}
            for mode in MODES:
                rankings[mode] = [{"article_id": "a1", "score": 1.0, "chunk_id": "chunk"}]
            run_rows = [{"query_id": "q0", "query_lang": "en", "need_type": "same_language", "rankings": rankings}] + [
                {"query_id": f"q{i}", "query_lang": "en", "need_type": "same_language",
                 "rankings": {mode: [] for mode in MODES}} for i in range(1, 48)]
            run_path.write_text(json.dumps({"snapshot_id": "snapshot", "queries_sha256": "queries",
                                            "status": "unjudged", "systems": list(MODES), "query_rows": run_rows}), encoding="utf-8")
            candidate = {"query_id": "q0", "candidate_id": "c001", "article_id": "a1", "systems": list(MODES)}
            packets = folder / "packets.jsonl"
            packets.write_text("{}\n", encoding="utf-8")
            pool_path.write_text(json.dumps({"run_sha256": _file_sha(run_path), "snapshot_id": "snapshot",
                                             "queries_sha256": "queries", "status": "unjudged",
                                             "packets_sha256": _file_sha(packets), "candidate_pairs": 1,
                                             "candidate_map": [candidate]}), encoding="utf-8")
            with patch("eval.snapshot_retrieval._require_frozen", return_value=(query_rows, {"queries_sha256": "queries"})), \
                    patch("eval.snapshot_retrieval._validate_run", return_value=run_rows):
                result = score_run(run_path, pool_path, folder / "missing-judgments.jsonl", output, packets)
            self.assertEqual(result["status"], "incomplete")
            self.assertIsNone(result["metrics"])
            self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()

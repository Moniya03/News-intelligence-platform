import tempfile
import unittest
from pathlib import Path

from eval import LegacyEvaluationDisabled
from eval.cluster_eval import load_articles_with_categories, run_cluster_eval
from eval.misinfo_eval import run_misinfo_eval
from eval.rag_eval import run_rag_eval
from eval.retrieval_flores import load_flores_data, run_flores_eval
from eval.retrieval_news import compute_metrics, load_eval_queries, run_news_retrieval_eval
from eval.run_all import main as run_all


class EvaluationHonestyTests(unittest.TestCase):
    def test_all_legacy_runners_fail_without_writing_results(self):
        runners = [
            run_cluster_eval,
            run_misinfo_eval,
            run_rag_eval,
            run_flores_eval,
            run_news_retrieval_eval,
        ]
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "existing.json"
            result.write_text("historical artifact", encoding="utf-8")
            for runner in runners:
                with self.subTest(runner=runner.__name__):
                    with self.assertRaises(LegacyEvaluationDisabled):
                        runner(result)
                    self.assertEqual(result.read_text(encoding="utf-8"), "historical artifact")

    def test_master_runner_is_disabled(self):
        with self.assertRaises(LegacyEvaluationDisabled):
            run_all()

    def test_data_loaders_do_not_substitute_benchmarks(self):
        with self.assertRaisesRegex(RuntimeError, "explicit relevance judgments"):
            load_eval_queries()
        with self.assertRaisesRegex(RuntimeError, "synthetic clustering samples"):
            load_articles_with_categories()
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "devtest.en").write_text("one sentence\n", encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                load_flores_data(tmp)

    def test_retrieval_metric_helper_still_computes_real_rankings(self):
        self.assertEqual(
            compute_metrics(["other", "relevant"], ["relevant"]),
            {"Recall@5": 1.0, "MRR": 0.5, "nDCG@10": 0.6309},
        )


if __name__ == "__main__":
    unittest.main()

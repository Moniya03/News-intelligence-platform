"""Focused tests for CUDA fp16 loading and CPU fp32 loading."""

import unittest
from unittest.mock import patch

from core.rerank import RerankModel


class TestRerankLoading(unittest.TestCase):
    @patch("sentence_transformers.CrossEncoder")
    @patch("torch.cuda.is_available")
    def test_fp16_is_requested_only_for_cuda(self, cuda_available, cross_encoder):
        cases = (
            ("cuda", True, {"torch_dtype": "float16"}),
            ("cuda", False, {}),
            ("cpu", True, {}),
        )
        for device, cuda_available_value, model_kwargs in cases:
            with self.subTest(device=device, cuda_available=cuda_available_value):
                cuda_available.return_value = cuda_available_value
                cross_encoder.reset_mock()

                model = RerankModel(device=device, fp16=True)

                self.assertEqual(model.backend, "cross_encoder")
                self.assertEqual(cross_encoder.call_args.kwargs["device"], "cuda" if device == "cuda" and cuda_available_value else "cpu")
                self.assertEqual(cross_encoder.call_args.kwargs["model_kwargs"], model_kwargs)


if __name__ == "__main__":
    unittest.main()

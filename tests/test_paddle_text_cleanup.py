import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_ROOT = REPO_ROOT / "apps" / "ocr-worker"
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from engines.paddle_engine import PaddleOCREngine


class PaddleTextCleanupTest(unittest.TestCase):
    def test_prediction_repairs_utf8_mojibake_and_normalizes_text(self) -> None:
        engine = PaddleOCREngine()
        prediction = [{
            "rec_texts": ["f（x）＝xｅˣ", "å f（n）（x）\u200b", "  答案：A\x00  "],
            "rec_scores": [0.9, 0.8, 1.0],
        }]

        result = engine._prediction_to_result(prediction)

        self.assertEqual(result.raw_text, "f(x)=xex\n则 f(n)(x)\n答案:A")
        self.assertEqual(result.raw_json["prediction"]["rec_texts"][1], "å f（n）（x）\u200b")
        self.assertAlmostEqual(result.confidence, 0.9)

    def test_cleanup_preserves_legitimate_latin_and_math_symbols(self) -> None:
        self.assertEqual(PaddleOCREngine._clean_text_line("café ∑ x²"), "café ∑ x2")


if __name__ == "__main__":
    unittest.main()
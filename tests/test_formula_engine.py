import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_ROOT = REPO_ROOT / "apps" / "ocr-worker"
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from engines.base import OCREngineError
from engines.formula_engine import FormulaOCREngine


class FormulaEngineTest(unittest.TestCase):
    def test_prediction_extracts_latex(self) -> None:
        latex, raw = FormulaOCREngine._prediction_to_latex({"res": {"rec_formula": r"\frac{x}{y}"}})
        self.assertEqual(latex, r"\frac{x}{y}")
        self.assertEqual(raw["res"]["rec_formula"], r"\frac{x}{y}")

    def test_prediction_rejects_empty_latex(self) -> None:
        with self.assertRaises(OCREngineError):
            FormulaOCREngine._prediction_to_latex({"res": {"rec_formula": ""}})


if __name__ == "__main__":
    unittest.main()

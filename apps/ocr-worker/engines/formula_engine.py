import importlib.util
import os
from pathlib import Path
import tempfile
from typing import Any

from .base import OCREngine, OCREngineError, OCRResult
from .paddle_engine import PaddleOCREngine
from .runtime import configure_nvidia_dll_paths


DEFAULT_FORMULA_MODEL = "PP-FormulaNet_plus-M"
DEFAULT_DEVICE = "gpu"


class FormulaOCREngine(OCREngine):
    name = "formula"

    def __init__(self) -> None:
        self.device = os.getenv("FORMULA_DEVICE", os.getenv("PADDLEOCR_DEVICE", DEFAULT_DEVICE))
        self.model_name = os.getenv("FORMULA_MODEL", DEFAULT_FORMULA_MODEL)
        self.model_dir = os.getenv("FORMULA_MODEL_DIR")
        self._model = None

    def recognize(self, image_bytes: bytes, job: dict) -> OCRResult:
        prepared_bytes, preprocessing = PaddleOCREngine._prepare_image(image_bytes)
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(prepared_bytes)
                tmp_path = Path(tmp.name)
            predictions = list(self._get_model().predict(str(tmp_path), batch_size=1))
            if not predictions:
                raise OCREngineError("Formula model returned no prediction.")
            latex, raw_result = self._prediction_to_latex(predictions[0])
            return OCRResult(
                raw_json={
                    "formula": True,
                    "model_name": self.model_name,
                    "device": self.device,
                    "preprocessing": preprocessing,
                    "prediction": raw_result,
                },
                raw_text=latex,
                model_name=self.model_name,
                confidence=None,
            )
        finally:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink()

    def _get_model(self):
        if self._model is not None:
            return self._model
        missing = [name for name in ("paddleocr", "paddle", "tokenizers", "ftfy") if importlib.util.find_spec(name) is None]
        if missing:
            raise OCREngineError(f"Formula OCR dependencies are missing: {', '.join(missing)}.")
        configure_nvidia_dll_paths()
        try:
            from paddleocr import FormulaRecognition
            kwargs: dict[str, Any] = {"model_name": self.model_name, "device": self.device}
            if self.model_dir:
                kwargs["model_dir"] = self.model_dir
            self._model = FormulaRecognition(**kwargs)
        except Exception as exc:
            raise OCREngineError(f"Failed to initialize formula model {self.model_name}: {exc}") from exc
        return self._model

    @staticmethod
    def _prediction_to_latex(prediction: Any) -> tuple[str, dict[str, Any]]:
        value = getattr(prediction, "json", prediction)
        if callable(value):
            value = value()
        safe = PaddleOCREngine._json_safe(value)
        result = safe.get("res", safe) if isinstance(safe, dict) else {}
        latex = str(result.get("rec_formula") or "").strip()
        if not latex:
            raise OCREngineError("Formula model returned an empty LaTeX result.")
        return latex, safe

import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

from .base import OCREngine, OCREngineError, OCRResult


DEFAULT_DEVICE = "gpu"
DEFAULT_LANG = "ch"
DEFAULT_MODEL_ROOT = r"D:\Code\WB\wrongbook-models\paddleocr"
DEFAULT_DET_MODEL = "PP-OCRv6_medium_det"
DEFAULT_REC_MODEL = "PP-OCRv6_medium_rec"


class PaddleOCREngine(OCREngine):
    name = "paddle"

    def __init__(self) -> None:
        self.device = os.getenv("PADDLEOCR_DEVICE", DEFAULT_DEVICE)
        self.lang = os.getenv("PADDLEOCR_LANG", DEFAULT_LANG)
        self.model_root = Path(os.getenv("MODEL_ROOT", DEFAULT_MODEL_ROOT))
        self._ocr = None

    def recognize(self, image_bytes: bytes, job: dict) -> OCRResult:
        suffix = self._suffix_from_job(job)
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(image_bytes)
                tmp_path = Path(tmp.name)

            prediction = self._get_ocr().predict(str(tmp_path))
            return self._prediction_to_result(prediction)
        finally:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink()

    def _get_ocr(self):
        if self._ocr is not None:
            return self._ocr

        missing = self._missing_dependencies()
        if missing:
            raise OCREngineError(self._missing_dependency_message(missing))

        self._configure_nvidia_dll_paths()

        try:
            import paddleocr
            from paddleocr import PaddleOCR
        except Exception as exc:
            raise OCREngineError(f"Failed to import PaddleOCR: {exc}") from exc

        kwargs: dict[str, Any] = {
            "lang": self.lang,
            "device": self.device,
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
        }
        kwargs.update(self._local_model_kwargs())

        try:
            self._ocr = PaddleOCR(**kwargs)
        except Exception as exc:
            raise OCREngineError(f"Failed to initialize PaddleOCR: {exc}") from exc

        self._paddleocr_version = getattr(paddleocr, "__version__", "unknown")
        return self._ocr

    def _local_model_kwargs(self) -> dict[str, str]:
        det_dir = self.model_root / DEFAULT_DET_MODEL
        rec_dir = self.model_root / DEFAULT_REC_MODEL

        if det_dir.is_dir() and rec_dir.is_dir():
            return {
                "text_detection_model_dir": det_dir.as_posix(),
                "text_recognition_model_dir": rec_dir.as_posix(),
            }

        if os.getenv("MODEL_ROOT"):
            raise OCREngineError(
                "OCR_ENGINE=paddle is selected, but MODEL_ROOT does not contain the expected "
                f"PaddleOCR model directories: {det_dir} and {rec_dir}."
            )

        return {}

    def _prediction_to_result(self, prediction: Any) -> OCRResult:
        first = prediction[0] if isinstance(prediction, list) and prediction else prediction

        rec_texts = self._get_field(first, "rec_texts") or []
        rec_scores = self._get_field(first, "rec_scores") or []
        raw_text = "\n".join(str(text) for text in rec_texts)
        confidence = self._average_score(rec_scores)
        compact_prediction = self._compact_prediction(first)

        return OCRResult(
            raw_json={
                "paddleocr": True,
                "device": self.device,
                "lang": self.lang,
                "paddleocr_version": getattr(self, "_paddleocr_version", "unknown"),
                "prediction": compact_prediction,
            },
            raw_text=raw_text,
            model_name=f"paddleocr-{getattr(self, '_paddleocr_version', 'unknown')}",
            confidence=confidence,
        )

    def _compact_prediction(self, first: Any) -> dict[str, Any]:
        fields = (
            "rec_texts",
            "rec_scores",
            "dt_polys",
            "rec_polys",
            "rec_boxes",
            "textline_orientation_angles",
            "text_type",
        )
        compact = {}
        for field in fields:
            value = self._get_field(first, field)
            if value is not None:
                compact[field] = self._json_safe(value)
        return compact

    @staticmethod
    def _get_field(item: Any, name: str) -> Any:
        if isinstance(item, dict):
            return item.get(name)
        return getattr(item, name, None)

    @classmethod
    def _json_safe(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): cls._json_safe(val) for key, val in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._json_safe(item) for item in value]
        if hasattr(value, "tolist"):
            return cls._json_safe(value.tolist())
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    @staticmethod
    def _average_score(scores: Any) -> float | None:
        if not scores:
            return None
        values = [float(score) for score in scores]
        return sum(values) / len(values)

    @staticmethod
    def _suffix_from_job(job: dict) -> str:
        file_path = str(job.get("file_path") or "")
        suffix = Path(file_path).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
            return suffix
        return ".png"

    @staticmethod
    def _configure_nvidia_dll_paths() -> None:
        if os.name != "nt":
            return

        site_packages = Path(sys.prefix) / "Lib" / "site-packages"
        candidates = [
            site_packages / "nvidia" / "cu13" / "bin" / "x86_64",
            site_packages / "nvidia" / "cudnn" / "bin",
        ]
        for path in candidates:
            if not path.is_dir():
                continue
            path_text = str(path)
            os.environ["PATH"] = path_text + os.pathsep + os.environ.get("PATH", "")
            try:
                os.add_dll_directory(path_text)
            except (AttributeError, FileNotFoundError, OSError):
                pass

    @staticmethod
    def _missing_dependency_message(missing: list[str]) -> str:
        return (
            "OCR_ENGINE=paddle cannot run because PaddleOCR dependencies are not installed. "
            f"Missing: {', '.join(missing)}. "
            "Install PaddleOCR and PaddlePaddle on the Windows laptop, keep model files out of Git, "
            "and keep OCR_ENGINE=mock on the server."
        )

    @staticmethod
    def _missing_dependencies() -> list[str]:
        missing = []

        if importlib.util.find_spec("paddleocr") is None:
            missing.append("paddleocr")

        if importlib.util.find_spec("paddle") is None:
            missing.append("paddlepaddle (import name: paddle)")

        return missing
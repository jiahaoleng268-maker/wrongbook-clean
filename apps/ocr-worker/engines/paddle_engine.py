import importlib.util

from .base import OCREngine, OCREngineError, OCRResult


class PaddleOCREngine(OCREngine):
    name = "paddle"

    def recognize(self, image_bytes: bytes, job: dict) -> OCRResult:
        missing = self._missing_dependencies()
        if missing:
            raise OCREngineError(
                "OCR_ENGINE=paddle cannot run because PaddleOCR dependencies are not installed. "
                f"Missing: {', '.join(missing)}. "
                "Keep OCR_ENGINE=mock for now, or install PaddleOCR and PaddlePaddle "
                "on the Windows laptop later."
            )

        raise OCREngineError(
            "OCR_ENGINE=paddle is selected, but PaddleOCR model wiring is not implemented yet. "
            "Keep OCR_ENGINE=mock until the Paddle engine is completed."
        )

    @staticmethod
    def _missing_dependencies() -> list[str]:
        missing = []

        if importlib.util.find_spec("paddleocr") is None:
            missing.append("paddleocr")

        if importlib.util.find_spec("paddle") is None:
            missing.append("paddlepaddle (import name: paddle)")

        return missing

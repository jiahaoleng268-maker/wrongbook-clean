from .base import OCREngine, OCREngineError, OCRResult
from .mock_engine import MockOCREngine
from .formula_engine import FormulaOCREngine
from .paddle_engine import PaddleOCREngine


def build_engine(name: str) -> OCREngine:
    mode = (name or "mock").strip().lower()

    if mode == "mock":
        return MockOCREngine()

    if mode == "paddle":
        return PaddleOCREngine()

    if mode == "formula":
        return FormulaOCREngine()

    raise OCREngineError(
        f"Unsupported OCR_ENGINE={name!r}. Use OCR_ENGINE=mock, OCR_ENGINE=paddle, or OCR_ENGINE=formula."
    )


__all__ = [
    "OCREngine",
    "OCREngineError",
    "OCRResult",
    "MockOCREngine",
    "FormulaOCREngine",
    "PaddleOCREngine",
    "build_engine",
]

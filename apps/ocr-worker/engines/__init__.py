from .base import OCREngine, OCREngineError, OCRResult
from .mock_engine import MockOCREngine
from .paddle_engine import PaddleOCREngine


def build_engine(name: str) -> OCREngine:
    mode = (name or "mock").strip().lower()

    if mode == "mock":
        return MockOCREngine()

    if mode == "paddle":
        return PaddleOCREngine()

    raise OCREngineError(
        f"Unsupported OCR_ENGINE={name!r}. Use OCR_ENGINE=mock or OCR_ENGINE=paddle."
    )


__all__ = [
    "OCREngine",
    "OCREngineError",
    "OCRResult",
    "MockOCREngine",
    "PaddleOCREngine",
    "build_engine",
]

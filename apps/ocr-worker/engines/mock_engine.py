from .base import OCREngine, OCRResult


MOCK_RAW_TEXT = "mock OCR text from worker"


class MockOCREngine(OCREngine):
    name = "mock"

    def recognize(self, image_bytes: bytes, job: dict) -> OCRResult:
        return OCRResult(
            raw_json={"mock": True},
            raw_text=MOCK_RAW_TEXT,
            model_name="mock-ocr-worker",
            confidence=1.0,
        )

from dataclasses import dataclass
from typing import Any, Optional


class OCREngineError(Exception):
    pass


@dataclass(frozen=True)
class OCRResult:
    raw_json: Any
    raw_text: str
    model_name: str
    confidence: Optional[float] = None


class OCREngine:
    name = "base"

    def recognize(self, image_bytes: bytes, job: dict) -> OCRResult:
        raise NotImplementedError

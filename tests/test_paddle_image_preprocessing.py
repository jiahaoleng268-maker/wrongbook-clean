from io import BytesIO
import sys
import unittest
from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_ROOT = REPO_ROOT / "apps" / "ocr-worker"
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from engines.base import OCREngineError
from engines.paddle_engine import PaddleOCREngine


class PaddleImagePreprocessingTest(unittest.TestCase):
    def test_prepare_image_applies_exif_orientation(self) -> None:
        source = Image.new("RGB", (40, 20), "white")
        exif = Image.Exif()
        exif[274] = 6
        encoded = BytesIO()
        source.save(encoded, format="JPEG", exif=exif)

        prepared_bytes, metadata = PaddleOCREngine._prepare_image(encoded.getvalue())
        with Image.open(BytesIO(prepared_bytes)) as prepared:
            self.assertEqual(prepared.size, (20, 40))
            self.assertEqual(prepared.format, "PNG")

        self.assertEqual(metadata["exif_orientation"], 6)
        self.assertTrue(metadata["exif_transposed"])
        self.assertEqual(metadata["original_size"], [40, 20])
        self.assertEqual(metadata["prepared_size"], [20, 40])

    def test_prepare_image_rejects_invalid_data(self) -> None:
        with self.assertRaises(OCREngineError):
            PaddleOCREngine._prepare_image(b"not an image")


if __name__ == "__main__":
    unittest.main()

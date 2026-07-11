import argparse
from difflib import SequenceMatcher
import json
import os
from pathlib import Path
import sys
import time


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_ROOT = REPO_ROOT / "apps" / "ocr-worker"
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from engines import build_engine


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def normalize_for_score(text: str) -> str:
    return "".join(text.split())


def evaluate_image(engine, image_path: Path) -> dict:
    expected_path = image_path.with_suffix(".txt")
    expected_text = expected_path.read_text(encoding="utf-8") if expected_path.exists() else None
    started = time.monotonic()
    result = engine.recognize(image_path.read_bytes(), {"file_path": str(image_path)})
    duration_ms = int((time.monotonic() - started) * 1000)
    similarity = None
    if expected_text is not None:
        similarity = SequenceMatcher(None, normalize_for_score(expected_text), normalize_for_score(result.raw_text)).ratio()
    return {
        "image": str(image_path),
        "expected_file": str(expected_path) if expected_path.exists() else None,
        "duration_ms": duration_ms,
        "confidence": result.confidence,
        "similarity": similarity,
        "recognized_text": result.raw_text,
        "expected_text": expected_text,
        "model_name": result.model_name,
        "raw_json": result.raw_json,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate WrongBook OCR against local image/text samples.")
    parser.add_argument("input", type=Path, help="An image file or directory containing image samples.")
    parser.add_argument("--engine", default=os.getenv("OCR_ENGINE", "paddle"))
    parser.add_argument("--output", type=Path, default=Path("data/ocr-evaluation/report.json"))
    args = parser.parse_args()
    images = [args.input] if args.input.is_file() else sorted(path for path in args.input.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES)
    if not images:
        parser.error("No supported images found.")
    engine = build_engine(args.engine)
    results = [evaluate_image(engine, image) for image in images]
    scored = [item["similarity"] for item in results if item["similarity"] is not None]
    report = {
        "engine": args.engine,
        "image_count": len(results),
        "scored_count": len(scored),
        "average_similarity": sum(scored) / len(scored) if scored else None,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("engine", "image_count", "scored_count", "average_similarity")}, ensure_ascii=False))
    print(f"Report: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from contextlib import asynccontextmanager
from datetime import datetime
from hashlib import sha256
import os
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from apps.api.app.database import get_db, init_db
from apps.api.app.models import OCRJob, Question, QuestionAsset


UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"message": "WrongBook API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


def _validate_upload(file: UploadFile) -> str:
    content_type = file.content_type or ""
    filename = file.filename or ""
    extension = Path(filename).suffix.lower()

    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type. Use image/jpeg, image/png, or image/webp.",
        )

    if extension not in ALLOWED_IMAGE_TYPES[content_type]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported or mismatched file extension. Use .jpg, .jpeg, .png, or .webp.",
        )

    return extension


@app.post("/api/questions/upload")
async def upload_question_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    extension = _validate_upload(file)
    today = datetime.now()
    target_dir = UPLOAD_DIR / f"{today:%Y}" / f"{today:%m}" / f"{today:%d}"
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / f"{uuid4().hex}{extension}"
    digest = sha256()
    total_size = 0

    try:
        with target_path.open("wb") as output:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break

                total_size += len(chunk)
                if total_size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Uploaded file is too large. Maximum size is 20MB.",
                    )

                digest.update(chunk)
                output.write(chunk)

        question = Question(status="draft", source="upload")
        db.add(question)
        db.flush()

        file_path = target_path.as_posix()
        asset = QuestionAsset(
            question_id=question.id,
            file_path=file_path,
            asset_type="original",
            sha256=digest.hexdigest(),
        )
        db.add(asset)
        db.flush()

        ocr_job = OCRJob(
            question_id=question.id,
            asset_id=asset.id,
            status="pending",
        )
        db.add(ocr_job)
        db.flush()

        question_id = question.id
        asset_id = asset.id
        ocr_job_id = ocr_job.id
        ocr_job_status = ocr_job.status
        db.commit()

        return {
            "question_id": question_id,
            "asset_id": asset_id,
            "ocr_job_id": ocr_job_id,
            "file_path": file_path,
            "status": ocr_job_status,
        }
    except HTTPException:
        db.rollback()
        if target_path.exists():
            target_path.unlink()
        raise
    except Exception:
        db.rollback()
        if target_path.exists():
            target_path.unlink()
        raise
    finally:
        await file.close()

from contextlib import asynccontextmanager
from datetime import datetime
from hashlib import sha256
from secrets import compare_digest
from typing import Any, Optional
import json
import os
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from apps.api.app.database import get_db, init_db
from apps.api.app.models import OCRJob, Question, QuestionAsset, utc_now


UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
STATIC_DIR = Path(__file__).parent / "static"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
}
DEFAULT_WORKER_NAME = "unknown-worker"
ALLOWED_QUESTION_STATUSES = {"draft", "recognized", "corrected", "archived"}


class OCRResultPayload(BaseModel):
    raw_json: Any = None
    raw_text: Optional[str] = None
    model_name: Optional[str] = None
    duration_ms: Optional[int] = None
    confidence: Optional[float] = None


class OCRFailPayload(BaseModel):
    error_message: str


class QuestionUpdatePayload(BaseModel):
    subject: Optional[str] = None
    title: Optional[str] = None
    corrected_text: Optional[str] = None
    question_type: Optional[str] = None
    difficulty: Optional[str] = None
    status: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/app/static", StaticFiles(directory=STATIC_DIR), name="web-static")


@app.get("/")
def read_root():
    return {"message": "WrongBook API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/app", include_in_schema=False)
@app.get("/app/", include_in_schema=False)
def web_app():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/app/service-worker.js", include_in_schema=False)
def web_service_worker():
    return FileResponse(
        STATIC_DIR / "service-worker.js",
        media_type="application/javascript",
    )


@app.get("/app/{path:path}", include_in_schema=False)
def web_app_fallback(path: str):
    return FileResponse(STATIC_DIR / "index.html")


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None

    return token.strip()


def require_worker_token(
    x_worker_token: Optional[str] = Header(default=None, alias="X-Worker-Token"),
    authorization: Optional[str] = Header(default=None),
) -> None:
    expected_token = os.getenv("WORKER_TOKEN") or "change-me"
    supplied_token = (x_worker_token or "").strip() or _extract_bearer_token(authorization)

    if not supplied_token or not compare_digest(supplied_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing worker token.",
        )


def _normalize_worker_name(worker_name: Optional[str]) -> str:
    if not worker_name:
        return DEFAULT_WORKER_NAME

    stripped = worker_name.strip()
    return stripped or DEFAULT_WORKER_NAME


def _serialize_raw_json(raw_json: Any) -> Optional[str]:
    if raw_json is None:
        return None

    if isinstance(raw_json, str):
        return raw_json

    return json.dumps(raw_json, ensure_ascii=False, separators=(",", ":"))


def _job_response(job: OCRJob) -> dict:
    return {
        "ocr_job_id": job.id,
        "question_id": job.question_id,
        "asset_id": job.asset_id,
        "file_path": job.asset.file_path if job.asset else None,
        "status": job.status,
        "worker_name": job.worker_name,
        "model_name": job.model_name,
        "raw_json": job.raw_json,
        "raw_text": job.raw_text,
        "confidence": job.confidence,
        "duration_ms": job.duration_ms,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "updated_at": job.updated_at,
    }


def _asset_response(asset: QuestionAsset) -> dict:
    return {
        "asset_id": asset.id,
        "question_id": asset.question_id,
        "file_path": asset.file_path,
        "asset_type": asset.asset_type,
        "width": asset.width,
        "height": asset.height,
        "sha256": asset.sha256,
        "created_at": asset.created_at,
        "updated_at": asset.updated_at,
    }


def _sorted_assets(question: Question) -> list[QuestionAsset]:
    return sorted(question.assets, key=lambda asset: asset.id)


def _sorted_ocr_jobs(question: Question) -> list[OCRJob]:
    return sorted(question.ocr_jobs, key=lambda job: job.id)


def _question_summary_response(question: Question) -> dict:
    assets = _sorted_assets(question)
    jobs = _sorted_ocr_jobs(question)
    latest_job = jobs[-1] if jobs else None
    first_asset = assets[0] if assets else None

    return {
        "question_id": question.id,
        "subject": question.subject,
        "title": question.title,
        "raw_text": question.raw_text,
        "corrected_text": question.corrected_text,
        "question_type": question.question_type,
        "difficulty": question.difficulty,
        "source": question.source,
        "status": question.status,
        "asset_count": len(assets),
        "first_asset": _asset_response(first_asset) if first_asset else None,
        "latest_ocr_job": _job_response(latest_job) if latest_job else None,
        "created_at": question.created_at,
        "updated_at": question.updated_at,
    }


def _question_detail_response(question: Question) -> dict:
    detail = _question_summary_response(question)
    detail["assets"] = [_asset_response(asset) for asset in _sorted_assets(question)]
    detail["ocr_jobs"] = [_job_response(job) for job in _sorted_ocr_jobs(question)]
    return detail


def _get_ocr_job_or_404(db: Session, job_id: int) -> OCRJob:
    job = db.get(OCRJob, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OCR job not found.",
        )

    return job


def _get_question_or_404(db: Session, question_id: int) -> Question:
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )

    return question


def _resolve_upload_file_path(stored_file_path: str) -> Path:
    upload_root = UPLOAD_DIR.resolve()
    candidate_path = Path(stored_file_path)

    if not candidate_path.is_absolute():
        candidate_path = Path.cwd() / candidate_path

    resolved_path = candidate_path.resolve()
    try:
        resolved_path.relative_to(upload_root)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset file not found.",
        )

    return resolved_path


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


@app.get("/api/assets/{asset_id}/file")
def get_asset_file(asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(QuestionAsset, asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset file not found.",
        )

    file_path = _resolve_upload_file_path(asset.file_path)
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset file not found.",
        )

    return FileResponse(file_path)


@app.get("/api/ocr/jobs/next", dependencies=[Depends(require_worker_token)])
def claim_next_ocr_job(
    worker_name: Optional[str] = Header(default=None, alias="X-Worker-Name"),
    db: Session = Depends(get_db),
):
    normalized_worker_name = _normalize_worker_name(worker_name)

    while True:
        pending_job = (
            db.query(OCRJob)
            .filter(OCRJob.status == "pending")
            .order_by(OCRJob.created_at.asc(), OCRJob.id.asc())
            .first()
        )

        if not pending_job:
            return {"job": None}

        pending_job_id = pending_job.id
        now = utc_now()
        updated_count = (
            db.query(OCRJob)
            .filter(OCRJob.id == pending_job_id, OCRJob.status == "pending")
            .update(
                {
                    OCRJob.status: "running",
                    OCRJob.worker_name: normalized_worker_name,
                    OCRJob.started_at: now,
                    OCRJob.updated_at: now,
                },
                synchronize_session=False,
            )
        )

        if updated_count:
            db.commit()
            job = _get_ocr_job_or_404(db, pending_job_id)
            return {"job": _job_response(job)}

        db.rollback()


@app.get("/api/ocr/jobs/{job_id}", dependencies=[Depends(require_worker_token)])
def get_ocr_job(job_id: int, db: Session = Depends(get_db)):
    job = _get_ocr_job_or_404(db, job_id)
    return {"job": _job_response(job)}


@app.post("/api/ocr/jobs/{job_id}/heartbeat", dependencies=[Depends(require_worker_token)])
def heartbeat_ocr_job(job_id: int, db: Session = Depends(get_db)):
    job = _get_ocr_job_or_404(db, job_id)
    job.updated_at = utc_now()
    db.commit()
    db.refresh(job)
    return {"job": _job_response(job)}


@app.post("/api/ocr/jobs/{job_id}/result", dependencies=[Depends(require_worker_token)])
def submit_ocr_result(
    job_id: int,
    payload: OCRResultPayload,
    db: Session = Depends(get_db),
):
    job = _get_ocr_job_or_404(db, job_id)
    now = utc_now()

    job.status = "succeeded"
    job.finished_at = now
    job.updated_at = now
    job.raw_json = _serialize_raw_json(payload.raw_json)
    job.raw_text = payload.raw_text
    job.model_name = payload.model_name
    job.duration_ms = payload.duration_ms
    job.confidence = payload.confidence
    job.error_message = None

    question = db.get(Question, job.question_id)
    if question:
        question.raw_text = payload.raw_text
        if payload.raw_text and question.status == "draft":
            question.status = "recognized"
        question.updated_at = now

    db.commit()
    db.refresh(job)
    return {"job": _job_response(job)}


@app.post("/api/ocr/jobs/{job_id}/fail", dependencies=[Depends(require_worker_token)])
def fail_ocr_job(
    job_id: int,
    payload: OCRFailPayload,
    db: Session = Depends(get_db),
):
    job = _get_ocr_job_or_404(db, job_id)
    now = utc_now()

    job.status = "failed"
    job.finished_at = now
    job.updated_at = now
    job.error_message = payload.error_message

    db.commit()
    db.refresh(job)
    return {"job": _job_response(job)}


@app.post("/api/ocr/jobs/{job_id}/retry", dependencies=[Depends(require_worker_token)])
def retry_ocr_job(job_id: int, db: Session = Depends(get_db)):
    job = _get_ocr_job_or_404(db, job_id)
    if job.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed OCR jobs can be retried.",
        )

    now = utc_now()
    job.status = "pending"
    job.error_message = None
    job.started_at = None
    job.finished_at = None
    job.updated_at = now

    db.commit()
    db.refresh(job)
    return {"job": _job_response(job)}



@app.get("/api/questions")
def list_questions(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    subject: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Question)

    if status_filter:
        query = query.filter(Question.status == status_filter)

    if subject:
        query = query.filter(Question.subject == subject)

    if q and q.strip():
        pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Question.title.ilike(pattern),
                Question.raw_text.ilike(pattern),
                Question.corrected_text.ilike(pattern),
                Question.subject.ilike(pattern),
            )
        )

    total = query.count()
    questions = (
        query.order_by(Question.created_at.desc(), Question.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "items": [_question_summary_response(question) for question in questions],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.get("/api/questions/{question_id}")
def get_question(question_id: int, db: Session = Depends(get_db)):
    question = _get_question_or_404(db, question_id)
    return {"question": _question_detail_response(question)}


@app.patch("/api/questions/{question_id}")
def update_question(
    question_id: int,
    payload: QuestionUpdatePayload,
    db: Session = Depends(get_db),
):
    question = _get_question_or_404(db, question_id)
    updates = payload.model_dump(exclude_unset=True)

    if "status" in updates and updates["status"] not in ALLOWED_QUESTION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid question status.",
        )

    for field, value in updates.items():
        setattr(question, field, value)

    if updates:
        question.updated_at = utc_now()
        db.commit()
        db.refresh(question)

    return {"question": _question_detail_response(question)}

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

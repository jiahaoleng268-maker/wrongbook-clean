from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import compare_digest
from typing import Any, Optional
import json
import os
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from apps.api.app.database import engine, get_db, init_db
from apps.api.app.models import (
    Chapter,
    KnowledgePoint,
    MistakeTag,
    OCRJob,
    Question,
    QuestionAsset,
    Review,
    Source,
    question_knowledge_points,
    utc_now,
)


UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
STATIC_DIR = Path(__file__).parent / "static"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_FORMULA_CROP_BYTES = 5 * 1024 * 1024
MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_IMPORT_QUESTIONS = 500
CHUNK_SIZE = 1024 * 1024
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
}
DEFAULT_WORKER_NAME = "unknown-worker"
ALLOWED_QUESTION_STATUSES = {"draft", "recognized", "corrected", "archived"}
ALLOWED_REVIEW_RESULTS = {"again", "hard", "good", "easy"}
MAX_MISTAKE_TAGS_PER_QUESTION = 20
MAX_KNOWLEDGE_POINTS_PER_QUESTION = 30
ALLOWED_ASSET_TYPES = {"question_image", "answer_image", "solution_image", "draft_image", "source_page", "attachment", "original", "formula_crop"}


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
    raw_text: Optional[str] = None
    corrected_text: Optional[str] = None
    question_type: Optional[str] = None
    difficulty: Optional[str] = None
    source: Optional[str] = None
    source_id: Optional[int] = None
    chapter_id: Optional[int] = None
    source_page: Optional[str] = None
    answer_text: Optional[str] = None
    solution_text: Optional[str] = None
    personal_solution: Optional[str] = None
    wrong_answer: Optional[str] = None
    mistake_analysis: Optional[str] = None
    key_steps: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    knowledge_point_ids: list[int] = []
    mistake_tag_names: list[str] = []


class SourceCreatePayload(BaseModel):
    name: str
    source_type: Optional[str] = None
    subject: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    file_path: Optional[str] = None
    description: Optional[str] = None


class SourceUpdatePayload(BaseModel):
    name: Optional[str] = None
    source_type: Optional[str] = None
    subject: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    file_path: Optional[str] = None
    description: Optional[str] = None


class ChapterCreatePayload(BaseModel):
    source_id: int
    name: str
    parent_id: Optional[int] = None
    sort_order: int = 0
    description: Optional[str] = None

class ChapterUpdatePayload(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None
    description: Optional[str] = None


class QuestionBulkUpdatePayload(BaseModel):
    question_ids: list[int]
    source_id: Optional[int] = None
    chapter_id: Optional[int] = None
    status: Optional[str] = None
    knowledge_point_ids: list[int] = []
    mistake_tag_names: list[str] = []

class AssetUpdatePayload(BaseModel):
    asset_type: str


class MistakeTagUpdatePayload(BaseModel):
    names: list[str]


class KnowledgePointCreatePayload(BaseModel):
    name: str
    subject: Optional[str] = None
    parent_id: Optional[int] = None


class KnowledgePointUpdatePayload(BaseModel):
    ids: list[int]


class ReviewCreatePayload(BaseModel):
    due_at: datetime


class ReviewCompletePayload(BaseModel):
    result: str
    next_due_at: Optional[datetime] = None


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


@app.get("/health/details")
def detailed_health_check():
    database_ok = False
    database_error = None
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_ok = True
    except Exception as exc:
        database_error = str(exc)

    upload_path = UPLOAD_DIR.resolve()
    upload_parent = upload_path if upload_path.exists() else upload_path.parent
    uploads_writable = upload_parent.exists() and os.access(upload_parent, os.W_OK)
    disk = shutil.disk_usage(upload_parent if upload_parent.exists() else Path.cwd())
    minimum_free_bytes = int(os.getenv("MIN_FREE_DISK_BYTES", str(1024 * 1024 * 1024)))
    disk_ok = disk.free >= minimum_free_bytes
    overall_ok = database_ok and uploads_writable and disk_ok
    return {
        "status": "ok" if overall_ok else "degraded",
        "database": {"ok": database_ok, "error": database_error},
        "uploads": {"path": str(upload_path), "writable": uploads_writable},
        "disk": {
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "minimum_free_bytes": minimum_free_bytes,
            "ok": disk_ok,
        },
    }


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
        "engine_name": job.engine_name,
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


def _knowledge_point_response(point: KnowledgePoint) -> dict:
    return {
        "knowledge_point_id": point.id,
        "subject": point.subject,
        "name": point.name,
        "parent_id": point.parent_id,
        "created_at": point.created_at,
        "updated_at": point.updated_at,
    }


def _mistake_tag_response(tag: MistakeTag) -> dict:
    return {
        "mistake_tag_id": tag.id,
        "name": tag.name,
        "created_at": tag.created_at,
        "updated_at": tag.updated_at,
    }


def _review_response(review: Review) -> dict:
    return {
        "review_id": review.id,
        "question_id": review.question_id,
        "due_at": review.due_at,
        "reviewed_at": review.reviewed_at,
        "result": review.result,
        "next_due_at": review.next_due_at,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
    }


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _normalize_mistake_tag_names(names: list[str]) -> list[str]:
    if len(names) > MAX_MISTAKE_TAGS_PER_QUESTION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A question can have at most {MAX_MISTAKE_TAGS_PER_QUESTION} mistake tags.",
        )

    normalized_names = []
    seen_names = set()
    for raw_name in names:
        name = raw_name.strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mistake tag names cannot be empty.",
            )
        if len(name) > 255:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mistake tag names cannot exceed 255 characters.",
            )

        normalized_key = name.casefold()
        if normalized_key not in seen_names:
            seen_names.add(normalized_key)
            normalized_names.append(name)

    return normalized_names


def _sorted_assets(question: Question) -> list[QuestionAsset]:
    return sorted(question.assets, key=lambda asset: asset.id)


def _sorted_ocr_jobs(question: Question) -> list[OCRJob]:
    return sorted(question.ocr_jobs, key=lambda job: job.id)


def _sorted_knowledge_points(question: Question) -> list[KnowledgePoint]:
    return sorted(
        question.knowledge_points,
        key=lambda point: ((point.subject or "").casefold(), point.name.casefold(), point.id),
    )


def _sorted_mistake_tags(question: Question) -> list[MistakeTag]:
    return sorted(question.mistake_tags, key=lambda tag: (tag.name.casefold(), tag.id))


def _sorted_reviews(question: Question) -> list[Review]:
    return sorted(question.reviews, key=lambda review: (review.due_at, review.id))


def _next_pending_review(question: Question) -> Optional[Review]:
    pending_reviews = [review for review in question.reviews if review.reviewed_at is None]
    return min(pending_reviews, key=lambda review: (review.due_at, review.id), default=None)


def _source_response(source: Source) -> dict:
    return {
        "source_id": source.id,
        "name": source.name,
        "source_type": source.source_type,
        "subject": source.subject,
        "author": source.author,
        "publisher": source.publisher,
        "file_path": source.file_path,
        "description": source.description,
        "created_at": source.created_at,
        "updated_at": source.updated_at,
    }


def _chapter_response(chapter: Chapter) -> dict:
    return {
        "chapter_id": chapter.id,
        "source_id": chapter.source_id,
        "parent_id": chapter.parent_id,
        "name": chapter.name,
        "sort_order": chapter.sort_order,
        "description": chapter.description,
        "created_at": chapter.created_at,
        "updated_at": chapter.updated_at,
    }

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
        "source_id": question.source_id,
        "source_record": _source_response(question.source_record) if question.source_record else None,
        "chapter_id": question.chapter_id,
        "chapter": _chapter_response(question.chapter) if question.chapter else None,
        "source_page": question.source_page,
        "answer_text": question.answer_text,
        "solution_text": question.solution_text,
        "personal_solution": question.personal_solution,
        "wrong_answer": question.wrong_answer,
        "mistake_analysis": question.mistake_analysis,
        "key_steps": question.key_steps,
        "notes": question.notes,
        "status": question.status,
        "asset_count": len(assets),
        "first_asset": _asset_response(first_asset) if first_asset else None,
        "latest_ocr_job": _job_response(latest_job) if latest_job else None,
        "knowledge_points": [
            _knowledge_point_response(point) for point in _sorted_knowledge_points(question)
        ],
        "mistake_tags": [_mistake_tag_response(tag) for tag in _sorted_mistake_tags(question)],
        "next_review": (
            _review_response(next_review)
            if (next_review := _next_pending_review(question))
            else None
        ),
        "created_at": question.created_at,
        "updated_at": question.updated_at,
    }


def _question_detail_response(question: Question) -> dict:
    detail = _question_summary_response(question)
    detail["assets"] = [_asset_response(asset) for asset in _sorted_assets(question)]
    detail["ocr_jobs"] = [_job_response(job) for job in _sorted_ocr_jobs(question)]
    detail["reviews"] = [_review_response(review) for review in _sorted_reviews(question)]
    return detail


def _export_filename(question: Question, extension: str) -> str:
    base = (question.title or f"question-{question.id}").strip()
    safe = "".join(character if character.isalnum() or character in {"-", "_"} else "-" for character in base)
    safe = "-".join(part for part in safe.split("-") if part)[:80] or f"question-{question.id}"
    return f"{safe}.{extension}"


def _question_export_payload(question: Question) -> dict:
    detail = _question_detail_response(question)
    return {
        "format": "wrongbook-question",
        "version": 1,
        "exported_at": utc_now(),
        "question": detail,
    }


def _optional_import_text(value: Any, field: str, max_length: Optional[int] = None) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field} must be a string or null.")
    normalized = value.strip()
    if not normalized:
        return None
    if max_length is not None and len(normalized) > max_length:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field} cannot exceed {max_length} characters.")
    return normalized


def _import_question_items(payload: Any) -> list[dict]:
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported WrongBook JSON version.")
    export_format = payload.get("format")
    if export_format == "wrongbook-question":
        items = [payload.get("question")]
    elif export_format == "wrongbook-question-collection":
        items = payload.get("questions")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported WrongBook JSON format.")
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Import must contain at least one question.")
    if len(items) > MAX_IMPORT_QUESTIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Import cannot contain more than {MAX_IMPORT_QUESTIONS} questions.")
    if not all(isinstance(item, dict) for item in items):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Every imported question must be an object.")
    return items


def _find_or_create_import_knowledge_point(db: Session, name: str, subject: Optional[str]) -> KnowledgePoint:
    query = db.query(KnowledgePoint).filter(func.lower(KnowledgePoint.name) == name.casefold())
    query = query.filter(KnowledgePoint.subject.is_(None)) if subject is None else query.filter(func.lower(KnowledgePoint.subject) == subject.casefold())
    point = query.first()
    if point is None:
        point = KnowledgePoint(name=name, subject=subject)
        db.add(point)
        db.flush()
    return point


def _find_or_create_import_mistake_tag(db: Session, name: str) -> MistakeTag:
    tag = db.query(MistakeTag).filter(func.lower(MistakeTag.name) == name.casefold()).first()
    if tag is None:
        tag = MistakeTag(name=name)
        db.add(tag)
        db.flush()
    return tag


def _create_imported_question(db: Session, item: dict) -> Question:
    question_status = item.get("status", "draft")
    if question_status not in ALLOWED_QUESTION_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid imported question status: {question_status}.")
    question = Question(
        subject=_optional_import_text(item.get("subject"), "subject", 100),
        title=_optional_import_text(item.get("title"), "title", 255),
        raw_text=_optional_import_text(item.get("raw_text"), "raw_text"),
        corrected_text=_optional_import_text(item.get("corrected_text"), "corrected_text"),
        question_type=_optional_import_text(item.get("question_type"), "question_type", 100),
        difficulty=_optional_import_text(item.get("difficulty"), "difficulty", 50),
        source=_optional_import_text(item.get("source"), "source", 255),
        status=question_status,
    )
    db.add(question)
    raw_points = item.get("knowledge_points", [])
    if not isinstance(raw_points, list) or len(raw_points) > MAX_KNOWLEDGE_POINTS_PER_QUESTION:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid imported knowledge points.")
    seen_points = set()
    for raw_point in raw_points:
        if not isinstance(raw_point, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Imported knowledge points must be objects.")
        name = _optional_import_text(raw_point.get("name"), "knowledge point name", 255)
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Knowledge point name cannot be empty.")
        point_subject = _optional_import_text(raw_point.get("subject"), "knowledge point subject", 100)
        key = ((point_subject or "").casefold(), name.casefold())
        if key not in seen_points:
            seen_points.add(key)
            question.knowledge_points.append(_find_or_create_import_knowledge_point(db, name, point_subject))
    raw_tags = item.get("mistake_tags", [])
    if not isinstance(raw_tags, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid imported mistake tags.")
    tag_values = [raw_tag.get("name") if isinstance(raw_tag, dict) else raw_tag for raw_tag in raw_tags]
    if not all(isinstance(value, str) for value in tag_values):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Imported mistake tag names must be strings.")
    tag_names = _normalize_mistake_tag_names(tag_values)
    question.mistake_tags = [_find_or_create_import_mistake_tag(db, name) for name in tag_names]
    db.flush()
    return question


def _question_markdown(question: Question) -> str:
    title = question.title or f"错题 #{question.id}"
    metadata = [
        ("科目", question.subject or "未设置"),
        ("题型", question.question_type or "未设置"),
        ("难度", question.difficulty or "未设置"),
        ("状态", question.status),
        ("知识点", "、".join(point.name for point in _sorted_knowledge_points(question)) or "无"),
        ("错因标签", "、".join(tag.name for tag in _sorted_mistake_tags(question)) or "无"),
    ]
    lines = [f"# {title}", "", *[f"- **{label}**：{value}" for label, value in metadata], ""]
    lines.extend(["## 校正文", "", question.corrected_text or "（暂无校正文）", ""])
    lines.extend(["## OCR 原文", "", question.raw_text or "（暂无 OCR 原文）", ""])
    lines.extend(["## 复习记录", ""])
    reviews = _sorted_reviews(question)
    if reviews:
        for review in reviews:
            reviewed = review.reviewed_at.isoformat() if review.reviewed_at else "待复习"
            lines.append(f"- {review.due_at.isoformat()} · {review.result or 'pending'} · {reviewed}")
    else:
        lines.append("- 暂无复习记录")
    return "\n".join(lines) + "\n"


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


def _get_knowledge_point_or_404(db: Session, point_id: int) -> KnowledgePoint:
    point = db.get(KnowledgePoint, point_id)
    if not point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge point not found.",
        )
    return point


def _get_review_or_404(db: Session, review_id: int) -> Review:
    review = db.get(Review, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found.",
        )

    return review


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


@app.post("/api/questions/{question_id}/assets", status_code=status.HTTP_201_CREATED)
async def add_question_asset(
    question_id: int,
    asset_type: str = Form("question_image"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    question = _get_question_or_404(db, question_id)
    if asset_type not in ALLOWED_ASSET_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid asset type.")
    extension = _validate_upload(file)
    today = datetime.now()
    target_dir = UPLOAD_DIR / f"{today:%Y}" / f"{today:%m}" / f"{today:%d}"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{uuid4().hex}{extension}"
    digest = sha256(); total_size = 0
    try:
        with target_path.open("wb") as output:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk: break
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Uploaded file is too large. Maximum size is 20MB.")
                digest.update(chunk); output.write(chunk)
        asset = QuestionAsset(question_id=question.id, file_path=target_path.as_posix(), asset_type=asset_type, sha256=digest.hexdigest())
        db.add(asset); db.commit(); db.refresh(asset)
        return {"asset": _asset_response(asset), "question": _question_detail_response(question)}
    except Exception:
        db.rollback()
        if target_path.exists(): target_path.unlink()
        raise
    finally:
        await file.close()


@app.patch("/api/assets/{asset_id}")
def update_question_asset(asset_id: int, payload: AssetUpdatePayload, db: Session = Depends(get_db)):
    asset = db.get(QuestionAsset, asset_id)
    if asset is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    if payload.asset_type not in ALLOWED_ASSET_TYPES: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid asset type.")
    asset.asset_type = payload.asset_type; asset.updated_at = utc_now(); db.commit(); db.refresh(asset)
    return {"asset": _asset_response(asset)}


@app.delete("/api/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(QuestionAsset, asset_id)
    if asset is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    if asset.ocr_jobs: raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assets referenced by OCR history cannot be deleted.")
    file_path = _resolve_upload_file_path(asset.file_path)
    db.delete(asset); db.commit()
    if file_path.is_file(): file_path.unlink()

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
    if question and job.engine_name != "formula":
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



@app.get("/api/questions/stats")
def question_stats(
    knowledge_limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    total_questions = db.query(func.count(Question.id)).scalar() or 0
    status_rows = (
        db.query(Question.status, func.count(Question.id))
        .group_by(Question.status)
        .order_by(func.count(Question.id).desc(), Question.status.asc())
        .all()
    )
    subject_label = func.coalesce(func.nullif(func.trim(Question.subject), ""), "Uncategorized")
    subject_rows = (
        db.query(subject_label.label("subject"), func.count(Question.id).label("count"))
        .group_by(subject_label)
        .order_by(func.count(Question.id).desc(), subject_label.asc())
        .all()
    )
    knowledge_rows = (
        db.query(
            KnowledgePoint.id,
            KnowledgePoint.name,
            KnowledgePoint.subject,
            func.count(question_knowledge_points.c.question_id).label("question_count"),
        )
        .outerjoin(
            question_knowledge_points,
            question_knowledge_points.c.knowledge_point_id == KnowledgePoint.id,
        )
        .group_by(KnowledgePoint.id, KnowledgePoint.name, KnowledgePoint.subject)
        .order_by(
            func.count(question_knowledge_points.c.question_id).desc(),
            func.lower(KnowledgePoint.name).asc(),
            KnowledgePoint.id.asc(),
        )
        .limit(knowledge_limit)
        .all()
    )
    return {
        "total_questions": total_questions,
        "status_counts": {status_name: count for status_name, count in status_rows},
        "subject_counts": [
            {"subject": subject_name, "question_count": count}
            for subject_name, count in subject_rows
        ],
        "top_knowledge_points": [
            {
                "knowledge_point_id": point_id,
                "name": name,
                "subject": subject,
                "question_count": question_count,
            }
            for point_id, name, subject, question_count in knowledge_rows
        ],
    }


@app.get("/api/questions/export")
def export_questions(
    format: str = Query(default="json", pattern="^(json|markdown)$"),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    subject: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=500),
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
    questions = query.order_by(Question.created_at.desc(), Question.id.desc()).limit(limit).all()
    filters = {"status": status_filter, "subject": subject, "q": q.strip() if q and q.strip() else None}
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if format == "markdown":
        sections = ["# WrongBook 题目导出", "", f"- 总匹配数：{total}", f"- 本次导出数：{len(questions)}", ""]
        for question in questions:
            sections.append(_question_markdown(question).rstrip())
            sections.extend(["", "---", ""])
        return PlainTextResponse(
            "\n".join(sections).rstrip() + "\n",
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="wrongbook-export-{timestamp}.md"'},
        )
    payload = {
        "format": "wrongbook-question-collection",
        "version": 1,
        "exported_at": utc_now(),
        "filters": filters,
        "total_matching": total,
        "exported_count": len(questions),
        "questions": [_question_detail_response(question) for question in questions],
    }
    return JSONResponse(
        jsonable_encoder(payload),
        headers={"Content-Disposition": f'attachment; filename="wrongbook-export-{timestamp}.json"'},
    )


@app.post("/api/questions/import", status_code=status.HTTP_201_CREATED)
async def import_questions(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or ""
    if Path(filename).suffix.lower() != ".json":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Import file must use the .json extension.")
    content = await file.read(MAX_IMPORT_BYTES + 1)
    await file.close()
    if len(content) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"Import file cannot exceed {MAX_IMPORT_BYTES} bytes.")
    try:
        payload = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Import file must contain valid UTF-8 JSON.") from exc
    items = _import_question_items(payload)
    try:
        questions = [_create_imported_question(db, item) for item in items]
        db.commit()
        for question in questions:
            db.refresh(question)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    return {
        "imported_count": len(questions),
        "question_ids": [question.id for question in questions],
        "ignored_fields": ["id", "assets", "ocr_jobs", "reviews", "created_at", "updated_at"],
    }


@app.get("/api/sources")
def list_sources(db: Session = Depends(get_db)):
    sources = db.query(Source).order_by(func.lower(Source.name), Source.id).all()
    return {
        "items": [
            {
                **_source_response(source),
                "chapters": [
                    _chapter_response(chapter)
                    for chapter in sorted(source.chapters, key=lambda item: (item.sort_order, item.name.casefold(), item.id))
                ],
            }
            for source in sources
        ]
    }


@app.post("/api/sources", status_code=status.HTTP_201_CREATED)
def create_source(payload: SourceCreatePayload, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source name is required.")
    source = Source(
        name=name,
        source_type=payload.source_type.strip() if payload.source_type else None,
        subject=payload.subject.strip() if payload.subject else None,
        author=payload.author.strip() if payload.author else None,
        publisher=payload.publisher.strip() if payload.publisher else None,
        file_path=payload.file_path.strip() if payload.file_path else None,
        description=payload.description.strip() if payload.description else None,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return {"source": _source_response(source)}


@app.patch("/api/sources/{source_id}")
def update_source(source_id: int, payload: SourceUpdatePayload, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        updates["name"] = updates["name"].strip() if updates["name"] else ""
        if not updates["name"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source name is required.")
    for field, value in updates.items(): setattr(source, field, value.strip() if isinstance(value, str) else value)
    source.updated_at = utc_now(); db.commit(); db.refresh(source)
    return {"source": _source_response(source)}


@app.delete("/api/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")
    if source.questions or source.chapters: raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only empty sources can be deleted.")
    db.delete(source); db.commit()

@app.post("/api/chapters", status_code=status.HTTP_201_CREATED)
def create_chapter(payload: ChapterCreatePayload, db: Session = Depends(get_db)):
    source = db.get(Source, payload.source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found.")
    if payload.parent_id is not None:
        parent = db.get(Chapter, payload.parent_id)
        if parent is None or parent.source_id != source.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent chapter must belong to the source.")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chapter name is required.")
    chapter = Chapter(
        source_id=source.id,
        parent_id=payload.parent_id,
        name=name,
        sort_order=payload.sort_order,
        description=payload.description.strip() if payload.description else None,
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return {"chapter": _chapter_response(chapter)}

@app.patch("/api/chapters/{chapter_id}")
def update_chapter(chapter_id: int, payload: ChapterUpdatePayload, db: Session = Depends(get_db)):
    chapter = db.get(Chapter, chapter_id)
    if chapter is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found.")
    updates = payload.model_dump(exclude_unset=True)
    if "parent_id" in updates and updates["parent_id"] is not None:
        parent = db.get(Chapter, updates["parent_id"])
        if parent is None or parent.source_id != chapter.source_id or parent.id == chapter.id: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parent chapter.")
    if "name" in updates:
        updates["name"] = updates["name"].strip() if updates["name"] else ""
        if not updates["name"]: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chapter name is required.")
    for field, value in updates.items(): setattr(chapter, field, value.strip() if isinstance(value, str) else value)
    chapter.updated_at = utc_now(); db.commit(); db.refresh(chapter)
    return {"chapter": _chapter_response(chapter)}


@app.delete("/api/chapters/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chapter(chapter_id: int, db: Session = Depends(get_db)):
    chapter = db.get(Chapter, chapter_id)
    if chapter is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found.")
    if chapter.questions or chapter.children: raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only empty leaf chapters can be deleted.")
    db.delete(chapter); db.commit()

@app.get("/api/questions")
def list_questions(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    subject: Optional[str] = Query(default=None),
    source_id: Optional[int] = Query(default=None),
    chapter_id: Optional[int] = Query(default=None),
    smart_filter: Optional[str] = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Question)
    if status_filter: query = query.filter(Question.status == status_filter)
    if subject: query = query.filter(Question.subject == subject)
    if source_id is not None: query = query.filter(Question.source_id == source_id)
    if chapter_id is not None: query = query.filter(Question.chapter_id == chapter_id)
    if smart_filter == "unclassified": query = query.filter(Question.source_id.is_(None), Question.chapter_id.is_(None))
    elif smart_filter == "missing_answer": query = query.filter(or_(Question.answer_text.is_(None), func.trim(Question.answer_text) == ""))
    elif smart_filter == "missing_knowledge": query = query.filter(~Question.knowledge_points.any())
    elif smart_filter == "recent": query = query.filter(Question.created_at >= utc_now() - timedelta(days=7))
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        query = query.filter(or_(Question.title.ilike(pattern), Question.raw_text.ilike(pattern), Question.corrected_text.ilike(pattern), Question.subject.ilike(pattern)))
    sort_columns = {"created_at": Question.created_at, "updated_at": Question.updated_at, "title": Question.title, "subject": Question.subject, "question_type": Question.question_type, "difficulty": Question.difficulty, "status": Question.status, "source_page": Question.source_page}
    sort_column = sort_columns.get(sort_by)
    if sort_column is None: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid sort_by.")
    if sort_order not in {"asc", "desc"}: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid sort_order.")
    total = query.count()
    ordering = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    questions = query.order_by(ordering, Question.id.desc()).offset(offset).limit(limit).all()
    return {"items": [_question_summary_response(question) for question in questions], "total": total, "limit": limit, "offset": offset}

@app.get("/api/knowledge-points")
def list_knowledge_points(
    subject: Optional[str] = Query(default=None),
    parent_id: Optional[int] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(KnowledgePoint)
    if subject and subject.strip():
        query = query.filter(func.lower(KnowledgePoint.subject) == subject.strip().casefold())
    if parent_id is not None:
        query = query.filter(KnowledgePoint.parent_id == parent_id)
    if q and q.strip():
        query = query.filter(KnowledgePoint.name.ilike(f"%{q.strip()}%"))

    total = query.count()
    points = (
        query.order_by(
            func.lower(KnowledgePoint.subject),
            func.lower(KnowledgePoint.name),
            KnowledgePoint.id,
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [_knowledge_point_response(point) for point in points],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.post("/api/knowledge-points", status_code=status.HTTP_201_CREATED)
def create_knowledge_point(
    payload: KnowledgePointCreatePayload,
    db: Session = Depends(get_db),
):
    name = payload.name.strip()
    subject = payload.subject.strip() if payload.subject else None
    subject = subject or None
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Knowledge point name cannot be empty.")
    if len(name) > 255:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Knowledge point name cannot exceed 255 characters.")
    if subject and len(subject) > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Knowledge point subject cannot exceed 100 characters.")

    parent = None
    if payload.parent_id is not None:
        parent = _get_knowledge_point_or_404(db, payload.parent_id)
        if parent.subject != subject:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent and child knowledge points must use the same subject.",
            )

    duplicate_query = db.query(KnowledgePoint).filter(func.lower(KnowledgePoint.name) == name.casefold())
    duplicate_query = (
        duplicate_query.filter(KnowledgePoint.subject.is_(None))
        if subject is None
        else duplicate_query.filter(func.lower(KnowledgePoint.subject) == subject.casefold())
    )
    if duplicate_query.first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Knowledge point already exists for this subject.")

    point = KnowledgePoint(name=name, subject=subject, parent=parent)
    db.add(point)
    db.commit()
    db.refresh(point)
    return {"knowledge_point": _knowledge_point_response(point)}


@app.put("/api/questions/{question_id}/knowledge-points")
def replace_question_knowledge_points(
    question_id: int,
    payload: KnowledgePointUpdatePayload,
    db: Session = Depends(get_db),
):
    question = _get_question_or_404(db, question_id)
    unique_ids = list(dict.fromkeys(payload.ids))
    if len(unique_ids) > MAX_KNOWLEDGE_POINTS_PER_QUESTION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A question can have at most {MAX_KNOWLEDGE_POINTS_PER_QUESTION} knowledge points.",
        )

    points = []
    if unique_ids:
        points = db.query(KnowledgePoint).filter(KnowledgePoint.id.in_(unique_ids)).all()
        found_ids = {point.id for point in points}
        missing_ids = [point_id for point_id in unique_ids if point_id not in found_ids]
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Knowledge point not found: {missing_ids[0]}.",
            )
        points.sort(key=lambda point: unique_ids.index(point.id))

    question.knowledge_points = points
    question.updated_at = utc_now()
    db.commit()
    db.refresh(question)
    return {"question": _question_detail_response(question)}


@app.get("/api/mistake-tags")
def list_mistake_tags(
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(MistakeTag)
    if q and q.strip():
        query = query.filter(MistakeTag.name.ilike(f"%{q.strip()}%"))

    total = query.count()
    tags = (
        query.order_by(func.lower(MistakeTag.name), MistakeTag.id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [_mistake_tag_response(tag) for tag in tags],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.put("/api/questions/{question_id}/mistake-tags")
def replace_question_mistake_tags(
    question_id: int,
    payload: MistakeTagUpdatePayload,
    db: Session = Depends(get_db),
):
    question = _get_question_or_404(db, question_id)
    names = _normalize_mistake_tag_names(payload.names)
    tags = []
    for name in names:
        tag = (
            db.query(MistakeTag)
            .filter(func.lower(MistakeTag.name) == name.casefold())
            .first()
        )
        if not tag:
            tag = MistakeTag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)

    question.mistake_tags = tags
    question.updated_at = utc_now()
    db.commit()
    db.refresh(question)
    return {"question": _question_detail_response(question)}


@app.post("/api/questions/{question_id}/reviews", status_code=status.HTTP_201_CREATED)
def create_review(
    question_id: int,
    payload: ReviewCreatePayload,
    db: Session = Depends(get_db),
):
    question = _get_question_or_404(db, question_id)
    pending_review = (
        db.query(Review)
        .filter(Review.question_id == question_id, Review.reviewed_at.is_(None))
        .order_by(Review.due_at.asc(), Review.id.asc())
        .first()
    )
    if pending_review:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Question already has a pending review.",
        )

    review = Review(question_id=question.id, due_at=_normalize_datetime(payload.due_at))
    db.add(review)
    db.commit()
    db.refresh(review)
    return {"review": _review_response(review)}


@app.get("/api/reviews/history")
def review_history(
    result: Optional[str] = Query(default=None),
    question_id: Optional[int] = Query(default=None),
    reviewed_from: Optional[datetime] = Query(default=None),
    reviewed_to: Optional[datetime] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    if result is not None and result not in ALLOWED_REVIEW_RESULTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid review result.")
    start = _normalize_datetime(reviewed_from) if reviewed_from else None
    end = _normalize_datetime(reviewed_to) if reviewed_to else None
    if start and end and start > end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="reviewed_from must not be later than reviewed_to.")

    query = db.query(Review).filter(Review.reviewed_at.is_not(None))
    if result:
        query = query.filter(Review.result == result)
    if question_id is not None:
        query = query.filter(Review.question_id == question_id)
    if start:
        query = query.filter(Review.reviewed_at >= start)
    if end:
        query = query.filter(Review.reviewed_at <= end)

    total = query.count()
    reviews = query.order_by(Review.reviewed_at.desc(), Review.id.desc()).offset(offset).limit(limit).all()
    items = []
    for review in reviews:
        item = _review_response(review)
        item["question"] = _question_summary_response(review.question)
        items.append(item)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@app.get("/api/reviews/stats")
def review_stats(
    now: Optional[datetime] = Query(default=None),
    db: Session = Depends(get_db),
):
    current = _normalize_datetime(now) if now else utc_now()
    today_start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    seven_day_start = today_start - timedelta(days=6)

    due_count = db.query(Review).filter(
        Review.reviewed_at.is_(None),
        Review.due_at <= current,
    ).count()
    completed_today = db.query(Review).filter(
        Review.reviewed_at >= today_start,
        Review.reviewed_at < tomorrow_start,
    ).count()
    recent_reviews = db.query(Review).filter(
        Review.reviewed_at >= seven_day_start,
        Review.reviewed_at < tomorrow_start,
    ).all()
    result_counts = {result: 0 for result in sorted(ALLOWED_REVIEW_RESULTS)}
    for review in recent_reviews:
        if review.result in result_counts:
            result_counts[review.result] += 1
    completed_seven_days = len(recent_reviews)
    mastered_count = result_counts["good"] + result_counts["easy"]
    mastered_rate = mastered_count / completed_seven_days if completed_seven_days else None

    return {
        "as_of": current,
        "due_count": due_count,
        "completed_today": completed_today,
        "completed_seven_days": completed_seven_days,
        "result_counts_seven_days": result_counts,
        "mastered_rate_seven_days": mastered_rate,
    }


@app.get("/api/reviews/due")
def list_due_reviews(
    before: Optional[datetime] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    due_before = _normalize_datetime(before) if before else utc_now()
    query = db.query(Review).filter(
        Review.reviewed_at.is_(None),
        Review.due_at <= due_before,
    )
    total = query.count()
    reviews = query.order_by(Review.due_at.asc(), Review.id.asc()).offset(offset).limit(limit).all()
    items = []
    for review in reviews:
        item = _review_response(review)
        item["question"] = _question_summary_response(review.question)
        items.append(item)

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "before": due_before,
    }


@app.post("/api/reviews/{review_id}/complete")
def complete_review(
    review_id: int,
    payload: ReviewCompletePayload,
    db: Session = Depends(get_db),
):
    review = _get_review_or_404(db, review_id)
    if review.reviewed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Review is already completed.",
        )
    if payload.result not in ALLOWED_REVIEW_RESULTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid review result.",
        )

    reviewed_at = utc_now()
    next_due_at = _normalize_datetime(payload.next_due_at) if payload.next_due_at else None
    if next_due_at is not None and next_due_at <= reviewed_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="next_due_at must be later than the completion time.",
        )

    review.reviewed_at = reviewed_at
    review.result = payload.result
    review.next_due_at = next_due_at
    review.updated_at = reviewed_at

    next_review = None
    if next_due_at is not None:
        next_review = Review(question_id=review.question_id, due_at=next_due_at)
        db.add(next_review)

    db.commit()
    db.refresh(review)
    if next_review:
        db.refresh(next_review)

    return {
        "review": _review_response(review),
        "next_review": _review_response(next_review) if next_review else None,
    }


@app.get("/api/questions/{question_id}")
def get_question(question_id: int, db: Session = Depends(get_db)):
    question = _get_question_or_404(db, question_id)
    return {"question": _question_detail_response(question)}


@app.get("/api/questions/{question_id}/export")
def export_question(
    question_id: int,
    format: str = Query(default="json", pattern="^(json|markdown)$"),
    db: Session = Depends(get_db),
):
    question = _get_question_or_404(db, question_id)
    if format == "markdown":
        return PlainTextResponse(
            _question_markdown(question),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{_export_filename(question, "md")}"'},
        )
    return JSONResponse(
        jsonable_encoder(_question_export_payload(question)),
        headers={"Content-Disposition": f'attachment; filename="{_export_filename(question, "json")}"'},
    )


@app.post("/api/questions/{question_id}/archive")
def archive_question(question_id: int, db: Session = Depends(get_db)):
    question = _get_question_or_404(db, question_id)
    if question.status == "archived":
        return {"question": _question_detail_response(question)}
    question.status = "archived"
    question.updated_at = utc_now()
    db.commit()
    db.refresh(question)
    return {"question": _question_detail_response(question)}


@app.post("/api/questions/{question_id}/restore")
def restore_question(question_id: int, db: Session = Depends(get_db)):
    question = _get_question_or_404(db, question_id)
    if question.status != "archived":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Question is not archived.")
    question.status = "corrected"
    question.updated_at = utc_now()
    db.commit()
    db.refresh(question)
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid question status.")
    if "source_id" in updates and updates["source_id"] is not None and db.get(Source, updates["source_id"]) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid source_id.")
    if "chapter_id" in updates and updates["chapter_id"] is not None:
        chapter = db.get(Chapter, updates["chapter_id"])
        if chapter is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chapter_id.")
        effective_source_id = updates.get("source_id", question.source_id)
        if effective_source_id is not None and chapter.source_id != effective_source_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chapter does not belong to the selected source.")
        updates.setdefault("source_id", chapter.source_id)

    for field, value in updates.items():
        setattr(question, field, value)

    if updates:
        question.updated_at = utc_now()
        db.commit()
        db.expire_all()
        question = _get_question_or_404(db, question_id)

    return {"question": _question_detail_response(question)}

@app.post("/api/questions/{question_id}/ocr-jobs", status_code=status.HTTP_201_CREATED)
def create_question_ocr_job(question_id: int, db: Session = Depends(get_db)):
    question = _get_question_or_404(db, question_id)
    active_job = (
        db.query(OCRJob)
        .filter(OCRJob.question_id == question_id, OCRJob.status.in_(["pending", "running"]))
        .order_by(OCRJob.id.desc())
        .first()
    )
    if active_job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Question already has an active OCR job.",
        )
    asset = next(iter(_sorted_assets(question)), None)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Question has no image asset for OCR.",
        )
    job = OCRJob(question=question, asset=asset, status="pending", engine_name="paddle")
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"job": _job_response(job), "question": _question_detail_response(question)}


@app.post("/api/questions/{question_id}/formula-ocr", status_code=status.HTTP_201_CREATED)
async def create_formula_ocr_job(
    question_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    question = _get_question_or_404(db, question_id)
    active_job = (
        db.query(OCRJob)
        .filter(
            OCRJob.question_id == question_id,
            OCRJob.engine_name == "formula",
            OCRJob.status.in_(["pending", "running"]),
        )
        .first()
    )
    if active_job:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Question already has an active formula OCR job.")
    extension = _validate_upload(file)
    today = datetime.now()
    target_dir = UPLOAD_DIR / f"{today:%Y}" / f"{today:%m}" / f"{today:%d}"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"formula-{uuid4().hex}{extension}"
    digest = sha256()
    total_size = 0
    try:
        with target_path.open("wb") as output:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_FORMULA_CROP_BYTES:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Formula crop cannot exceed 5MB.")
                digest.update(chunk)
                output.write(chunk)
        asset = QuestionAsset(
            question_id=question.id,
            file_path=target_path.as_posix(),
            asset_type="formula_crop",
            sha256=digest.hexdigest(),
        )
        db.add(asset)
        db.flush()
        job = OCRJob(
            question_id=question.id,
            asset_id=asset.id,
            status="pending",
            engine_name="formula",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return {"job": _job_response(job), "asset": _asset_response(asset)}
    except Exception:
        db.rollback()
        if target_path.exists():
            target_path.unlink()
        raise
    finally:
        await file.close()


@app.post("/api/questions/bulk-update")
def bulk_update_questions(payload: QuestionBulkUpdatePayload, db: Session = Depends(get_db)):
    question_ids = sorted(set(payload.question_ids))
    if not question_ids or len(question_ids) > 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select between 1 and 200 questions.")
    if payload.status is not None and payload.status not in ALLOWED_QUESTION_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid question status.")
    if payload.source_id is not None and db.get(Source, payload.source_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid source_id.")
    if payload.chapter_id is not None:
        chapter = db.get(Chapter, payload.chapter_id)
        if chapter is None: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chapter_id.")
        if payload.source_id is not None and chapter.source_id != payload.source_id: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chapter does not belong to the selected source.")
    unique_point_ids = list(dict.fromkeys(payload.knowledge_point_ids))
    knowledge_points = db.query(KnowledgePoint).filter(KnowledgePoint.id.in_(unique_point_ids)).all() if unique_point_ids else []
    if len(knowledge_points) != len(unique_point_ids): raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more knowledge points were not found.")
    mistake_tags = []
    for name in _normalize_mistake_tag_names(payload.mistake_tag_names):
        tag = db.query(MistakeTag).filter(func.lower(MistakeTag.name) == name.casefold()).first()
        if tag is None: tag = MistakeTag(name=name); db.add(tag); db.flush()
        mistake_tags.append(tag)
    questions = db.query(Question).filter(Question.id.in_(question_ids)).all()
    if len(questions) != len(question_ids): raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more questions were not found.")
    for question in questions:
        if payload.source_id is not None: question.source_id = payload.source_id
        if payload.chapter_id is not None:
            chapter = db.get(Chapter, payload.chapter_id); question.chapter_id = chapter.id; question.source_id = chapter.source_id
        if payload.status is not None: question.status = payload.status
        existing_point_ids = {point.id for point in question.knowledge_points}
        question.knowledge_points.extend(point for point in knowledge_points if point.id not in existing_point_ids)
        existing_tag_ids = {tag.id for tag in question.mistake_tags}
        question.mistake_tags.extend(tag for tag in mistake_tags if tag.id not in existing_tag_ids)
        question.updated_at = utc_now()
    db.commit()
    return {"updated_count": len(questions), "question_ids": question_ids}

@app.post("/api/questions/manual", status_code=status.HTTP_201_CREATED)
async def create_manual_question(
    title: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    question_type: Optional[str] = Form(None),
    source_id: Optional[int] = Form(None),
    chapter_id: Optional[int] = Form(None),
    source_page: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    normalized_content = content.strip() if content else None
    if not normalized_content and file is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide PaddleOCR text or an image.")

    question = Question(
        title=title.strip() if title else None,
        subject=subject.strip() if subject else None,
        source=source.strip() if source else "PaddleOCR Web",
        question_type=question_type.strip() if question_type else None,
        source_id=source_id,
        chapter_id=chapter_id,
        source_page=source_page.strip() if source_page else None,
        raw_text=normalized_content,
        corrected_text=normalized_content,
        status="draft",
    )
    target_path = None
    try:
        db.add(question)
        db.flush()
        asset = None
        if file is not None:
            extension = _validate_upload(file)
            today = datetime.now()
            target_dir = UPLOAD_DIR / f"{today:%Y}" / f"{today:%m}" / f"{today:%d}"
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / f"{uuid4().hex}{extension}"
            digest = sha256()
            total_size = 0
            with target_path.open("wb") as output:
                while True:
                    chunk = await file.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    total_size += len(chunk)
                    if total_size > MAX_UPLOAD_BYTES:
                        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Uploaded file is too large. Maximum size is 20MB.")
                    digest.update(chunk)
                    output.write(chunk)
            asset = QuestionAsset(
                question_id=question.id,
                file_path=target_path.as_posix(),
                asset_type="original",
                sha256=digest.hexdigest(),
            )
            db.add(asset)
        db.commit()
        db.refresh(question)
        return {"question": _question_detail_response(question), "asset": _asset_response(asset) if asset else None}
    except Exception:
        db.rollback()
        if target_path and target_path.exists():
            target_path.unlink()
        raise
    finally:
        if file is not None:
            await file.close()

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
            engine_name="paddle",
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

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship

from apps.api.app.database import Base


def utc_now() -> datetime:
    return datetime.utcnow()


question_knowledge_points = Table(
    "question_knowledge_points",
    Base.metadata,
    Column("question_id", ForeignKey("questions.id"), primary_key=True),
    Column("knowledge_point_id", ForeignKey("knowledge_points.id"), primary_key=True),
)

question_mistake_tags = Table(
    "question_mistake_tags",
    Base.metadata,
    Column("question_id", ForeignKey("questions.id"), primary_key=True),
    Column("mistake_tag_id", ForeignKey("mistake_tags.id"), primary_key=True),
)


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String(100), nullable=True, index=True)
    title = Column(String(255), nullable=True)
    raw_text = Column(Text, nullable=True)
    corrected_text = Column(Text, nullable=True)
    question_type = Column(String(100), nullable=True)
    difficulty = Column(String(50), nullable=True)
    source = Column(String(255), nullable=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=True, index=True)
    source_page = Column(String(50), nullable=True)
    answer_text = Column(Text, nullable=True)
    solution_text = Column(Text, nullable=True)
    personal_solution = Column(Text, nullable=True)
    wrong_answer = Column(Text, nullable=True)
    mistake_analysis = Column(Text, nullable=True)
    key_steps = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="draft", index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    assets = relationship("QuestionAsset", back_populates="question", cascade="all, delete-orphan")
    ocr_jobs = relationship("OCRJob", back_populates="question", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="question", cascade="all, delete-orphan")
    attempts = relationship("Attempt", back_populates="question", cascade="all, delete-orphan")
    knowledge_points = relationship(
        "KnowledgePoint",
        secondary=question_knowledge_points,
        back_populates="questions",
    )
    source_record = relationship("Source", back_populates="questions")
    chapter = relationship("Chapter", back_populates="questions")
    mistake_tags = relationship(
        "MistakeTag",
        secondary=question_mistake_tags,
        back_populates="questions",
    )


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    source_type = Column(String(50), nullable=True, index=True)
    subject = Column(String(100), nullable=True, index=True)
    author = Column(String(255), nullable=True)
    publisher = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    chapters = relationship("Chapter", back_populates="source", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="source_record")


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("chapters.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    sort_order = Column(Integer, nullable=False, default=0)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    source = relationship("Source", back_populates="chapters")
    parent = relationship("Chapter", remote_side=[id], back_populates="children")
    children = relationship("Chapter", back_populates="parent")
    questions = relationship("Question", back_populates="chapter")

class QuestionAsset(Base):
    __tablename__ = "question_assets"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    asset_type = Column(String(50), nullable=False, default="original", index=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    sha256 = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    question = relationship("Question", back_populates="assets")
    ocr_jobs = relationship("OCRJob", back_populates="asset")


class OCRJob(Base):
    __tablename__ = "ocr_jobs"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("question_assets.id"), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    engine_name = Column(String(50), nullable=False, default="paddle", index=True)
    model_name = Column(String(255), nullable=True)
    worker_name = Column(String(255), nullable=True)
    raw_json = Column(Text, nullable=True)
    raw_text = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    question = relationship("Question", back_populates="ocr_jobs")
    asset = relationship("QuestionAsset", back_populates="ocr_jobs")


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String(100), nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("knowledge_points.id"), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    parent = relationship("KnowledgePoint", remote_side=[id], back_populates="children")
    children = relationship("KnowledgePoint", back_populates="parent")
    questions = relationship(
        "Question",
        secondary=question_knowledge_points,
        back_populates="knowledge_points",
    )


class MistakeTag(Base):
    __tablename__ = "mistake_tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    questions = relationship(
        "Question",
        secondary=question_mistake_tags,
        back_populates="mistake_tags",
    )


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    due_at = Column(DateTime, nullable=False, index=True)
    reviewed_at = Column(DateTime, nullable=True)
    result = Column(String(50), nullable=True)
    next_due_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    question = relationship("Question", back_populates="reviews")


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    answer_text = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    question = relationship("Question", back_populates="attempts")

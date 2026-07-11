from pathlib import Path
from urllib.parse import urlparse
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker


DEFAULT_DATABASE_URL = "sqlite:///./data/app.db"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    parsed = urlparse(database_url)
    if not parsed.scheme.startswith("sqlite"):
        return

    if database_url == "sqlite:///:memory:":
        return

    raw_path = parsed.path
    if raw_path.startswith("/") and not raw_path.startswith("//"):
        raw_path = raw_path[1:]

    db_path = Path(raw_path)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path

    db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_dir(DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db() -> None:
    from apps.api.app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _apply_lightweight_migrations()


def _apply_lightweight_migrations() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return
    columns = {column["name"] for column in inspect(engine).get_columns("ocr_jobs")}
    if "engine_name" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE ocr_jobs ADD COLUMN engine_name VARCHAR(50) NOT NULL DEFAULT 'paddle'"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_ocr_jobs_engine_name ON ocr_jobs (engine_name)"))

    question_columns = {column["name"] for column in inspect(engine).get_columns("questions")}
    additions = {
        "source_id": "INTEGER",
        "chapter_id": "INTEGER",
        "source_page": "VARCHAR(50)",
        "answer_text": "TEXT",
        "solution_text": "TEXT",
        "personal_solution": "TEXT",
        "wrong_answer": "TEXT",
        "mistake_analysis": "TEXT",
        "key_steps": "TEXT",
        "notes": "TEXT",
    }
    with engine.begin() as connection:
        for column_name, column_type in additions.items():
            if column_name not in question_columns:
                connection.execute(text(f"ALTER TABLE questions ADD COLUMN {column_name} {column_type}"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_questions_source_id ON questions (source_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_questions_chapter_id ON questions (chapter_id)"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

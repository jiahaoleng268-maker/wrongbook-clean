# WrongBook

WrongBook is a personal wrong-question collection and review tool. The goal is to let a phone browser or PWA upload photos of questions, let the server store and organize them, and let a Windows laptop run OCR work separately from the low-resource server.

## PC-first workflow

WrongBook now uses a PC-first organization workflow. Use PaddleOCR Web for document and formula recognition, then paste its text, Markdown, or LaTeX into **导入**. An optional source image can be attached at creation time. `POST /api/questions/manual` creates the question without creating an OCR job, so the main application no longer depends on a local OCR Worker.

The desktop interface uses a persistent left navigation with **题库** and **导入**. Review screens, local formula cropping, and rerun-OCR controls are frozen and hidden from the primary UI, while all historical OCR jobs, review rows, assets, and APIs remain intact for data safety and possible future reuse.

Recommended daily flow:

1. Parse a screenshot or PDF page in PaddleOCR Web.
2. Copy the recognized text/Markdown/LaTeX.
3. Open WrongBook **导入** and paste the result.
4. Optionally attach the original question image.
5. Create the question, then classify and correct it in **题库**.
## Current Status

The project is currently a lightweight FastAPI backend in `apps/api`, a static Web/PWA frontend served by the API, and a local OCR Worker in `apps/ocr-worker`. The Web/PWA supports question correction, mistake tags, knowledge point assignment, and review scheduling. It has health endpoints, the first SQLite/SQLAlchemy data model, local image upload, question browsing/editing APIs, mistake tagging and review scheduling APIs, polling-style OCR job endpoints, a safe uploaded-asset file endpoint, mock OCR mode, and local Windows PaddleOCR mode. It does not include server-side OCR processing.

## Local API Startup

Use the API requirements file:

```powershell
cd D:\Code\WB\wrongbook
.\.venv\Scripts\Activate.ps1
pip install -r apps\api\requirements.txt
python -m uvicorn apps.api.app.main:app --reload
```

The root `requirements.txt` is kept for compatibility, but `apps/api/requirements.txt` is the recommended dependency file for the API.

## Web App

Start the backend, then open:

```text
http://127.0.0.1:8000/app
```

The first frontend is intentionally small and dependency-free. It is served from `apps/api/app/static` and can:

- upload one question image from a browser or phone camera
- list recent questions
- open question details
- show the uploaded image and OCR text
- edit `corrected_text`, title, subject, question type, difficulty, and status

The frontend does not run OCR. OCR still happens in the separate Windows Worker.

## Database

The API uses SQLite for the first version. The default database URL is:

```env
DATABASE_URL=sqlite:///./data/app.db
```

Initialize the database tables manually with:

```powershell
python -m apps.api.app.init_db
```

The FastAPI app also initializes tables during startup. The real database file `data/app.db` must not be committed. The repository keeps only `data/.gitkeep` as an empty directory placeholder.

## Uploads

Uploaded image files are stored on disk under `UPLOAD_DIR`, which defaults to:

```env
UPLOAD_DIR=./data/uploads
```

Supported image types:

- `image/jpeg` with `.jpg` or `.jpeg`
- `image/png` with `.png`
- `image/webp` with `.webp`

Maximum file size: 20 MB.

Example upload:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/questions/upload" -F "file=@D:\path\to\question.jpg;type=image/jpeg"
```

The upload API stores the image path in SQLite, creates a draft `Question`, creates an original `QuestionAsset`, and creates a pending `OCRJob`. It does not run OCR.

## OCR Job API

The server exposes a small polling API for an external OCR Worker. The Worker runs elsewhere, claims pending jobs from SQLite, performs OCR outside the server, and posts the result back.

Worker requests require a token. Configure it with:

```env
WORKER_TOKEN=change-me
```

Pass the token with either header:

```text
X-Worker-Token: change-me
Authorization: Bearer change-me
```

Optional Worker name header:

```text
X-Worker-Name: windows-laptop-01
```

OCR job endpoints:

- `GET /api/ocr/jobs/next` claims the oldest pending job and marks it `running`
- `GET /api/ocr/jobs/{id}` returns one OCR job
- `POST /api/ocr/jobs/{id}/heartbeat` updates the job heartbeat timestamp and returns current status
- `POST /api/ocr/jobs/{id}/result` marks the job `succeeded` and writes `raw_text` to `Question.raw_text`
- `POST /api/ocr/jobs/{id}/fail` marks the job `failed` with an error message
- `POST /api/ocr/jobs/{id}/retry` moves a failed job back to `pending`

The server still does not run PaddleOCR or any OCR model.

## Mock OCR Worker

The mock Worker is a local development utility that exercises the OCR job flow without installing PaddleOCR. It polls the API, validates that the uploaded image file can be fetched through the backend, and submits predictable text.

Environment variables:

```env
SERVER_URL=http://127.0.0.1:8000
WORKER_TOKEN=change-me
WORKER_NAME=local-mock-worker
POLL_INTERVAL=3
OCR_ENGINE=mock
```

Supported worker engine modes:

- `OCR_ENGINE=mock` is the default and returns predictable fake OCR text.
- `OCR_ENGINE=paddle` runs the local Windows PaddleOCR engine when PaddleOCR, PaddlePaddle, and local models are available. It conservatively normalizes readable OCR text while retaining original recognition fields in `raw_json`. It is for the laptop Worker only, not the server.

Run continuously:

```powershell
python apps\ocr-worker\mock_worker.py
```

Process at most one polling cycle and exit:

```powershell
python apps\ocr-worker\mock_worker.py --once
```

## Tests

The integration tests use only the Python standard library plus the project runtime dependencies. They start a temporary local API server with an isolated SQLite database and upload directory, then verify the Web app shell, upload, asset download, OCR job lifecycle, and mock Worker flow.

Run tests from the repository root:

```powershell
cd D:\Code\WB\wrongbook
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests
```

## API Endpoints

- `GET /` returns `{"message":"WrongBook API is running"}`
- `GET /health` returns `{"status":"ok"}`
- `GET /health/details` checks the database, upload path, and free disk space
- `GET /app` serves the browser/PWA workflow for upload, correction, mistake tags, review scheduling, and due-review completion
- `POST /api/questions/upload` uploads one image and creates a pending OCR job
- `GET /api/questions` lists questions with OCR text and lightweight metadata
- `GET /api/questions/stats` returns status, subject, and knowledge-point aggregates
- `GET /api/questions/{id}` returns one question with assets and OCR jobs
- `PATCH /api/questions/{id}` updates corrected text and metadata
- `POST /api/questions/{id}/archive` safely archives a question
- `POST /api/questions/{id}/restore` restores an archived question
- `GET /api/questions/export` downloads a filtered JSON or Markdown question collection
- `GET /api/questions/{id}/export` downloads JSON or Markdown question data
- `GET /api/knowledge-points` lists reusable hierarchical knowledge points
- `POST /api/knowledge-points` creates one knowledge point
- `PUT /api/questions/{id}/knowledge-points` replaces a question's knowledge points
- `GET /api/mistake-tags` lists reusable mistake tags
- `PUT /api/questions/{id}/mistake-tags` replaces a question's mistake tags
- `POST /api/questions/{id}/reviews` schedules one pending review
- `GET /api/reviews/history` lists and filters completed review records
- `GET /api/reviews/due` lists due reviews
- `GET /api/reviews/stats` returns current and seven-day review statistics
- `POST /api/reviews/{id}/complete` records a review result and optionally schedules the next review
- `GET /api/assets/{asset_id}/file` returns an uploaded asset file only if it is under `UPLOAD_DIR`
- `GET /api/ocr/jobs/next` claims a pending OCR job for a token-authenticated Worker
- `GET /api/ocr/jobs/{id}` returns OCR job status and details
- `POST /api/ocr/jobs/{id}/heartbeat` updates OCR job activity
- `POST /api/ocr/jobs/{id}/result` stores OCR output and succeeds the job
- `POST /api/ocr/jobs/{id}/fail` stores failure details
- `POST /api/ocr/jobs/{id}/retry` retries a failed job

## Backup and Restore

Create and verify a backup containing SQLite data and uploaded images:

```powershell
.\.venv\Scripts\python.exe scripts\backup_restore.py backup
.\.venv\Scripts\python.exe scripts\backup_restore.py verify backups\wrongbook-YYYYMMDD-HHMMSS.zip
```

Stop the API before restore. Restore refuses existing targets unless `--replace` is provided; replacement preserves current data in a `pre-restore-*` directory. See `docs/backup-restore.md` for the full procedure.

## Repository Safety

Do not commit local environment files, virtual environments, runtime data, uploaded images, logs, model files, databases, or backups.

Keep these out of Git:

- `.venv/`
- `.env`
- `data/app.db`
- `data/uploads/`
- `*.db`
- `*.sqlite`
- `*.sqlite3`
- `uploads/`
- `logs/`
- `runtime/`
- `downloads/`
- `models/`
- backup folders and files

The server is intended to stay lightweight. OCR and large-model workloads must run outside the server, on the Windows laptop worker.

- 支持导入 WrongBook v1 JSON；导入始终创建新题目，并忽略旧 ID、图片、OCR 任务和复习历史。

## Mobile acceptance

Before a release, run the real-device checklist in `docs/mobile-acceptance.md`. Automated checks cover UTF-8 responses, PWA metadata, and narrow viewport layout, but camera behavior and home-screen installation still require a physical phone.

- Question details can create a new OCR job from the stored original image. Re-recognition updates OCR raw text only and preserves manual corrected text.

## Mobile navigation

On phone-width screens the Web/PWA uses a bottom directory navigation with Home, Library, Review, and Statistics views. Home provides separate camera capture and gallery selection inputs so browsers that force camera capture still allow existing photos to be selected through the gallery control. Desktop keeps the full dashboard layout.

- The mobile gallery picker supports multi-select and uploads selected images sequentially. Camera capture remains single-image.

## OCR evaluation

Run `python scripts/evaluate_ocr.py <image-or-directory>` on the Windows OCR laptop. The report is written under `data/ocr-evaluation/` by default and remains outside Git. PaddleOCR now applies EXIF orientation before recognition and records preprocessing metadata in `raw_json`.

## Experimental formula OCR

The Windows worker includes an experimental `OCR_ENGINE=formula` backed by `PP-FormulaNet_plus-M`. Install `apps/ocr-worker/requirements-formula.txt` after PaddleOCR. The model is cached outside Git under the user PaddleX model cache. Evaluation confirms that it recovers LaTeX structures such as fractions, roots, superscripts, and integral bounds, but broad page regions containing tables or answer lines can generate severe hallucinations. Formula OCR is available from the question detail page: choose **框选公式识别**, drag a tight rectangle, and submit the crop. The server stores it as a `formula_crop` asset and creates an OCR job with `engine_name=formula`. Formula results remain in OCR history and never overwrite normal OCR text or corrected text; use **插入校正文** to append a selected LaTeX result before saving.

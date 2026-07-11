# WrongBook

WrongBook is a personal wrong-question collection and review tool. The goal is to let a phone browser or PWA upload photos of questions, let the server store and organize them, and let a Windows laptop run OCR work separately from the low-resource server.

## Current Status

The project is currently a lightweight FastAPI backend in `apps/api` plus a local OCR Worker in `apps/ocr-worker`. It has health endpoints, the first SQLite/SQLAlchemy data model, local image upload, question browsing/editing APIs, polling-style OCR job endpoints, a safe uploaded-asset file endpoint, mock OCR mode, and local Windows PaddleOCR mode. It does not include server-side OCR processing or a frontend.

## Local API Startup

Use the API requirements file:

```powershell
cd D:\Code\WB\wrongbook
.\.venv\Scripts\Activate.ps1
pip install -r apps\api\requirements.txt
python -m uvicorn apps.api.app.main:app --reload
```

The root `requirements.txt` is kept for compatibility, but `apps/api/requirements.txt` is the recommended dependency file for the API.

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
- `OCR_ENGINE=paddle` runs the local Windows PaddleOCR engine when PaddleOCR, PaddlePaddle, and local models are available. It is for the laptop Worker only, not the server.

Run continuously:

```powershell
python apps\ocr-worker\mock_worker.py
```

Process at most one polling cycle and exit:

```powershell
python apps\ocr-worker\mock_worker.py --once
```

## Tests

The integration tests use only the Python standard library plus the project runtime dependencies. They start a temporary local API server with an isolated SQLite database and upload directory, then verify the upload, asset download, OCR job lifecycle, and mock Worker flow.

Run tests from the repository root:

```powershell
cd D:\Code\WB\wrongbook
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests
```

## API Endpoints

- `GET /` returns `{"message":"WrongBook API is running"}`
- `GET /health` returns `{"status":"ok"}`
- `POST /api/questions/upload` uploads one image and creates a pending OCR job
- `GET /api/questions` lists questions with OCR text and lightweight metadata
- `GET /api/questions/{id}` returns one question with assets and OCR jobs
- `PATCH /api/questions/{id}` updates corrected text and metadata
- `GET /api/assets/{asset_id}/file` returns an uploaded asset file only if it is under `UPLOAD_DIR`
- `GET /api/ocr/jobs/next` claims a pending OCR job for a token-authenticated Worker
- `GET /api/ocr/jobs/{id}` returns OCR job status and details
- `POST /api/ocr/jobs/{id}/heartbeat` updates OCR job activity
- `POST /api/ocr/jobs/{id}/result` stores OCR output and succeeds the job
- `POST /api/ocr/jobs/{id}/fail` stores failure details
- `POST /api/ocr/jobs/{id}/retry` retries a failed job

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

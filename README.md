# WrongBook

WrongBook is a personal wrong-question collection and review tool. The goal is to let a phone browser or PWA upload photos of questions, let the server store and organize them, and let a Windows laptop run OCR work separately from the low-resource server.

## Current Status

The project is currently a lightweight FastAPI backend in `apps/api`. It has basic health endpoints, the first SQLite/SQLAlchemy data model, database initialization logic, and a local image upload API. It does not yet include OCR business processing, an OCR worker, PaddleOCR, or a frontend.

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

## API Endpoints

- `GET /` returns `{"message":"WrongBook API is running"}`
- `GET /health` returns `{"status":"ok"}`
- `POST /api/questions/upload` uploads one image and creates a pending OCR job

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

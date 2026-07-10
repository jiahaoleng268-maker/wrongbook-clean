# WrongBook

WrongBook is a personal wrong-question collection and review tool. The goal is to let a phone browser or PWA upload photos of questions, let the server store and organize them, and let a Windows laptop run OCR work separately from the low-resource server.

## Current Status

The project is currently a lightweight FastAPI backend in `apps/api`. It has basic health endpoints plus the first SQLite/SQLAlchemy data model and database initialization logic. It does not yet include image upload, OCR business APIs, an OCR worker, or a frontend.

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

## API Endpoints

- `GET /` returns `{"message":"WrongBook API is running"}`
- `GET /health` returns `{"status":"ok"}`

## Repository Safety

Do not commit local environment files, virtual environments, runtime data, uploaded images, logs, model files, databases, or backups.

Keep these out of Git:

- `.venv/`
- `.env`
- `data/app.db`
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

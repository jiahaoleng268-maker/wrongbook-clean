# WrongBook

WrongBook is a personal wrong-question collection and review tool. The goal is to let a phone browser or PWA upload photos of questions, let the server store and organize them, and let a Windows laptop run OCR work separately from the low-resource server.

## Current Status

The project is currently a minimal FastAPI backend. It has been moved into `apps/api` and can be started locally, but it does not yet include SQLite models, image upload, OCR jobs, an OCR worker, or a frontend.

## Local API Startup

Use the API requirements file:

```powershell
cd D:\Code\WB\wrongbook
.\.venv\Scripts\Activate.ps1
pip install -r apps\api\requirements.txt
python -m uvicorn apps.api.app.main:app --reload
```

The root `requirements.txt` is kept for compatibility, but `apps/api/requirements.txt` is the recommended dependency file for the API.

## API Endpoints

- `GET /` returns `{"message":"WrongBook API is running"}`
- `GET /health` returns `{"status":"ok"}`

## Repository Safety

Do not commit local environment files, virtual environments, runtime data, uploaded images, logs, model files, databases, or backups.

Keep these out of Git:

- `.venv/`
- `.env`
- `data/`
- `uploads/`
- `logs/`
- `runtime/`
- `downloads/`
- `models/`
- backup folders and files

The server is intended to stay lightweight. OCR and large-model workloads must run outside the server, on the Windows laptop worker.

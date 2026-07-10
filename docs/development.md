# Development

This document describes local development on Windows.

## Repository

```text
D:\Code\WB\wrongbook
```

## Start Backend Locally

Open PowerShell:

```powershell
cd D:\Code\WB\wrongbook
.\.venv\Scripts\Activate.ps1
pip install -r apps\api\requirements.txt
python -m uvicorn apps.api.app.main:app --reload
```

The API should be available at:

```text
http://127.0.0.1:8000
```

## Initialize Database

The default SQLite database URL is:

```env
DATABASE_URL=sqlite:///./data/app.db
```

Create the SQLite tables manually with:

```powershell
python -m apps.api.app.init_db
```

The app also creates tables during FastAPI startup. Do not commit `data/app.db`.

## Test Current Endpoints

PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected results:

```json
{"message":"WrongBook API is running"}
```

```json
{"status":"ok"}
```

Curl:

```powershell
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/health
```

## Run Automated Tests

The current tests start a temporary API server with an isolated SQLite database and upload directory. They do not use `data/app.db`, do not use `data/uploads`, and do not require PaddleOCR.

PowerShell:

```powershell
cd D:\Code\WB\wrongbook
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests
```

## Git Safety

Before committing, check:

```powershell
git status --short
git status --short --ignored
```

Do not commit:

- `.venv/`
- `.env`
- SQLite database files
- uploaded images
- downloaded images
- logs
- runtime files
- PaddleOCR models
- backups

Documentation-only tasks should not modify backend business code.

## Dependency Rule

Use:

```powershell
pip install -r apps\api\requirements.txt
```

Do not introduce new dependencies unless a task explicitly requires them.

# WrongBook

WrongBook is a minimal FastAPI backend.

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

# OCR Worker

The OCR Worker is a Windows laptop process that will poll the server for OCR jobs, download images, run OCR locally, and submit OCR results back to the server.

The server should only manage jobs and store data. It should not run PaddleOCR.

## Windows Local Directories

Planned local paths:

```text
Code repository:
D:\Code\WB\wrongbook

PaddleOCR model directory:
D:\Code\WB\wrongbook-models\paddleocr

Worker runtime directory:
D:\Code\WB\wrongbook-runtime

Downloaded image directory:
D:\Code\WB\wrongbook-runtime\downloads

Log directory:
D:\Code\WB\wrongbook-runtime\logs

Temporary file directory:
D:\Code\WB\wrongbook-runtime\temp

Backup directory:
D:\Code\WB\wrongbook-backups
```

Runtime directories and model directories must not be committed to Git.

## Future Environment Variables

Example worker configuration:

```env
SERVER_URL=http://127.0.0.1:8000
WORKER_TOKEN=change-me
WORKER_NAME=windows-laptop-01
OCR_ENGINE=mock
POLL_INTERVAL=5
MODEL_ROOT=D:\Code\WB\wrongbook-models\paddleocr
RUNTIME_DIR=D:\Code\WB\wrongbook-runtime
DOWNLOAD_DIR=D:\Code\WB\wrongbook-runtime\downloads
LOG_DIR=D:\Code\WB\wrongbook-runtime\logs
TEMP_DIR=D:\Code\WB\wrongbook-runtime\temp
```

Do not commit real secrets. Keep real values in local `.env` files only.

## Server OCR Job API

The server-side OCR job API is implemented. It is intentionally small and polling-based, using SQLite records instead of Redis or Celery.

All Worker requests must include the Worker token from the server environment:

```env
WORKER_TOKEN=change-me
```

Pass it as either:

```text
X-Worker-Token: change-me
```

or:

```text
Authorization: Bearer change-me
```

Workers should also send a name when claiming jobs:

```text
X-Worker-Name: windows-laptop-01
```

Implemented endpoints:

- `GET /api/assets/{asset_id}/file`
- `GET /api/ocr/jobs/next`
- `GET /api/ocr/jobs/{id}`
- `POST /api/ocr/jobs/{id}/heartbeat`
- `POST /api/ocr/jobs/{id}/result`
- `POST /api/ocr/jobs/{id}/fail`
- `POST /api/ocr/jobs/{id}/retry`

## Worker Polling Flow

1. Poll for work:

```powershell
curl.exe -H "X-Worker-Token: change-me" -H "X-Worker-Name: windows-laptop-01" "http://127.0.0.1:8000/api/ocr/jobs/next"
```

If the response is:

```json
{"job": null}
```

the Worker should sleep for `POLL_INTERVAL` seconds and poll again.

If a job is returned, the server has already moved it from `pending` to `running` and recorded `worker_name` and `started_at`.

2. Read `job.asset_id` and fetch the image from the backend:

```powershell
curl.exe "http://127.0.0.1:8000/api/assets/1/file" -o question.jpg
```

The file endpoint only serves files from the configured `UPLOAD_DIR`, which defaults to `./data/uploads`. It returns HTTP 404 for missing files or stored paths outside the upload directory.

3. Send heartbeat while processing:

```powershell
curl.exe -X POST -H "X-Worker-Token: change-me" "http://127.0.0.1:8000/api/ocr/jobs/1/heartbeat"
```

4. Submit success:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/ocr/jobs/1/result" -H "X-Worker-Token: change-me" -H "Content-Type: application/json" -d "{\"raw_json\":{\"lines\":[{\"text\":\"2x + 3 = 7\",\"confidence\":0.98}]},\"raw_text\":\"2x + 3 = 7\",\"model_name\":\"mock-ocr\",\"duration_ms\":1234,\"confidence\":0.98}"
```

The server marks the job `succeeded`, stores OCR metadata, writes `finished_at`, and copies `raw_text` into `Question.raw_text`. It does not change `Question.corrected_text`.

5. Submit failure:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/ocr/jobs/1/fail" -H "X-Worker-Token: change-me" -H "Content-Type: application/json" -d "{\"error_message\":\"OCR engine timed out\"}"
```

The server marks the job `failed`, writes `finished_at`, and stores the error message.

6. Retry a failed job manually:

```powershell
curl.exe -X POST -H "X-Worker-Token: change-me" "http://127.0.0.1:8000/api/ocr/jobs/1/retry"
```

The server moves the same job row back to `pending`, clears `error_message`, `started_at`, and `finished_at`, and keeps the original record.

## Mock Worker

The mock Worker lives at:

```text
apps\ocr-worker\mock_worker.py
```

It does not install or use PaddleOCR. It uses only Python standard library modules.

Configuration defaults:

```env
SERVER_URL=http://127.0.0.1:8000
WORKER_TOKEN=change-me
WORKER_NAME=local-mock-worker
POLL_INTERVAL=3
OCR_ENGINE=mock
```

`OCR_ENGINE=mock` is the default and keeps the fast local verification flow.

`OCR_ENGINE=paddle` runs the real local PaddleOCR engine on the Windows laptop. If PaddleOCR/PaddlePaddle or the configured local model directories are missing, the Worker will claim the job, mark it `failed`, and store a clear setup error in `error_message`.

Run the API first:

```powershell
cd D:\Code\WB\wrongbook
.\.venv\Scripts\Activate.ps1
python -m uvicorn apps.api.app.main:app --reload
```

Then run the mock Worker continuously:

```powershell
python apps\ocr-worker\mock_worker.py
```

For a one-shot local verification, process at most one pending job and exit:

```powershell
python apps\ocr-worker\mock_worker.py --once
```

The mock Worker loop is:

1. call `GET /api/ocr/jobs/next`
2. sleep for `POLL_INTERVAL` seconds when the response is `{"job": null}`
3. when a job is returned, fetch `GET /api/assets/{asset_id}/file`
4. submit `raw_text = "mock OCR text from worker"` to `POST /api/ocr/jobs/{id}/result`
5. submit `POST /api/ocr/jobs/{id}/fail` if processing raises an error

## Worker Engine Modes

`OCR_ENGINE=mock` mode:

- does not install PaddleOCR
- polls real server-side OCR jobs
- fetches uploaded assets through the backend file endpoint
- returns predictable fake OCR text
- is implemented as the first end-to-end Worker loop

`OCR_ENGINE=paddle` mode:

- runs on the Windows laptop
- is present as a placeholder before PaddleOCR installation
- fails claimed jobs with a clear dependency/setup message while PaddleOCR is not installed or wired
- must not be enabled on the low-resource server
- will later load models from `MODEL_ROOT`
- will later submit real OCR text and status back to the server

## Current Rule

Do not install PaddleOCR on the server. Local Windows laptop setup details are recorded in `docs/paddleocr-local.md`.

The server-side OCR job API, mock Worker loop, automated tests, selectable OCR engine layer, and local PaddleOCR engine now exist. Keep the server free of OCR/model workloads.

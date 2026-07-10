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
OCR_MODE=mock
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

2. Read the image path from `job.file_path`.

For the current local development setup, the Worker may run on the same Windows machine as the server and read the path directly. A future remote Worker may need an image download endpoint; that is outside the current task.

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

## Planned Worker Modes

`mock` mode:

- does not install PaddleOCR
- polls or simulates OCR jobs
- returns predictable fake OCR text
- is used to verify the server job flow first
- should be implemented before PaddleOCR mode

`paddle` mode:

- runs on the Windows laptop
- loads models from `MODEL_ROOT`
- downloads images into `DOWNLOAD_DIR`
- writes logs into `LOG_DIR`
- uses `TEMP_DIR` for temporary files
- submits OCR text and status back to the server

## Current Rule

Do not install PaddleOCR yet.

The server-side OCR job API now exists. The next OCR-related step should be a mock Worker client that calls these endpoints and returns predictable fake OCR text. PaddleOCR installation and model wiring should happen only after the API and mock worker flow are stable.

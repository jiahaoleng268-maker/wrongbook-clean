# API

This document describes the current WrongBook API. The server is lightweight and does not run OCR or large models.

## Health

### GET /

Returns:

```json
{"message":"WrongBook API is running"}
```

### GET /health

Returns:

```json
{"status":"ok"}
```

## Upload Question Image

### POST /api/questions/upload

Uploads one wrong-question image and creates the initial database records needed for later OCR processing.

Request type:

```text
multipart/form-data
```

Required form field:

```text
file
```

Supported content types and extensions:

- `image/jpeg`: `.jpg`, `.jpeg`
- `image/png`: `.png`
- `image/webp`: `.webp`

Maximum file size: 20 MB.

The final saved filename uses a UUID plus the original extension. The user-provided filename is not used as the saved filename.

Example:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/questions/upload" -F "file=@D:\path\to\question.jpg;type=image/jpeg"
```

Successful response:

```json
{
  "question_id": 1,
  "asset_id": 1,
  "ocr_job_id": 1,
  "file_path": "data/uploads/2026/07/10/example.jpg",
  "status": "pending"
}
```

Side effects:

- saves the image file under `UPLOAD_DIR/YYYY/MM/DD/`
- creates a `Question` with `status = draft` and `source = upload`
- creates a `QuestionAsset` with `asset_type = original`
- creates an `OCRJob` with `status = pending`

Current scope:

- no OCR recognition
- no OCR Worker client
- no PaddleOCR
- no frontend
- no image binary data stored in SQLite

## Browse Questions

### GET /api/questions

Returns a paginated list of questions for the future frontend/PWA.

Query parameters:

- `status`: optional exact status filter, such as `draft`, `recognized`, `corrected`, or `archived`
- `subject`: optional exact subject filter
- `q`: optional text search across `title`, `raw_text`, `corrected_text`, and `subject`
- `limit`: optional page size, default `20`, maximum `100`
- `offset`: optional offset, default `0`

Example:

```powershell
curl.exe "http://127.0.0.1:8000/api/questions?status=recognized&limit=20&offset=0"
```

Response shape:

```json
{
  "items": [
    {
      "question_id": 1,
      "subject": "math",
      "title": "Derivative practice",
      "raw_text": "recognized OCR text",
      "corrected_text": null,
      "question_type": null,
      "difficulty": null,
      "source": "upload",
      "status": "recognized",
      "asset_count": 1,
      "first_asset": {},
      "latest_ocr_job": {},
      "created_at": "2026-07-11T10:00:00",
      "updated_at": "2026-07-11T10:01:00"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

## Get Question Detail

### GET /api/questions/{question_id}

Returns one question with all uploaded assets and OCR jobs.

Example:

```powershell
curl.exe "http://127.0.0.1:8000/api/questions/1"
```

Unknown IDs return HTTP 404.

## Update Question

### PATCH /api/questions/{question_id}

Updates user-editable question fields. This is intended for manually correcting OCR text and adding lightweight metadata before the frontend is built.

Supported fields:

- `subject`
- `title`
- `corrected_text`
- `question_type`
- `difficulty`
- `status`: one of `draft`, `recognized`, `corrected`, or `archived`

Example:

```powershell
curl.exe -X PATCH "http://127.0.0.1:8000/api/questions/1" -H "Content-Type: application/json" -d "{\"subject\":\"math\",\"corrected_text\":\"corrected OCR text\",\"status\":\"corrected\"}"
```

Invalid statuses return HTTP 400.
## Download Asset File

### GET /api/assets/{asset_id}/file

Returns the uploaded file for one `QuestionAsset`.

Safety rules:

- looks up the asset by `asset_id`
- resolves the stored path before serving the file
- only serves files under the configured `UPLOAD_DIR`, which defaults to `./data/uploads`
- returns HTTP 404 when the asset does not exist, the file is missing, or the stored path points outside `UPLOAD_DIR`
- does not expose arbitrary local filesystem paths

Example:

```powershell
curl.exe -o question.jpg "http://127.0.0.1:8000/api/assets/1/file"
```

## OCR Worker Authentication

All `/api/ocr/jobs/*` endpoints require a Worker token. The server reads it from:

```env
WORKER_TOKEN=change-me
```

The default is `change-me`. Use a different value for real local deployments.

Pass the token with either header:

```text
X-Worker-Token: change-me
```

or:

```text
Authorization: Bearer change-me
```

Missing or invalid tokens return HTTP 401.

Example unauthorized request:

```powershell
curl.exe -i "http://127.0.0.1:8000/api/ocr/jobs/next"
```

Expected status:

```text
HTTP/1.1 401 Unauthorized
```

## Claim Next OCR Job

### GET /api/ocr/jobs/next

Claims the oldest `pending` OCR job, marks it `running`, records `worker_name`, records `started_at`, and returns the job.

Optional header:

```text
X-Worker-Name: windows-laptop-01
```

Example:

```powershell
curl.exe -H "X-Worker-Token: change-me" -H "X-Worker-Name: windows-laptop-01" "http://127.0.0.1:8000/api/ocr/jobs/next"
```

Successful response with a job:

```json
{
  "job": {
    "ocr_job_id": 1,
    "question_id": 1,
    "asset_id": 1,
    "file_path": "data/uploads/2026/07/10/example.jpg",
    "status": "running",
    "worker_name": "windows-laptop-01",
    "model_name": null,
    "raw_json": null,
    "raw_text": null,
    "confidence": null,
    "duration_ms": null,
    "error_message": null,
    "created_at": "2026-07-10T12:00:00",
    "started_at": "2026-07-10T12:01:00",
    "finished_at": null,
    "updated_at": "2026-07-10T12:01:00"
  }
}
```

Successful response with no pending jobs:

```json
{
  "job": null
}
```

## Get OCR Job

### GET /api/ocr/jobs/{id}

Returns status and stored information for one OCR job.

Example:

```powershell
curl.exe -H "Authorization: Bearer change-me" "http://127.0.0.1:8000/api/ocr/jobs/1"
```

Response:

```json
{
  "job": {
    "ocr_job_id": 1,
    "question_id": 1,
    "asset_id": 1,
    "file_path": "data/uploads/2026/07/10/example.jpg",
    "status": "running",
    "worker_name": "windows-laptop-01",
    "model_name": null,
    "raw_json": null,
    "raw_text": null,
    "confidence": null,
    "duration_ms": null,
    "error_message": null,
    "created_at": "2026-07-10T12:00:00",
    "started_at": "2026-07-10T12:01:00",
    "finished_at": null,
    "updated_at": "2026-07-10T12:01:00"
  }
}
```

Unknown IDs return HTTP 404.

## Heartbeat OCR Job

### POST /api/ocr/jobs/{id}/heartbeat

Updates `updated_at` and returns current job status. This lets a Worker confirm the job still exists and see whether its status changed.

Example:

```powershell
curl.exe -X POST -H "X-Worker-Token: change-me" "http://127.0.0.1:8000/api/ocr/jobs/1/heartbeat"
```

Response:

```json
{
  "job": {
    "ocr_job_id": 1,
    "question_id": 1,
    "asset_id": 1,
    "file_path": "data/uploads/2026/07/10/example.jpg",
    "status": "running",
    "worker_name": "windows-laptop-01",
    "model_name": null,
    "raw_json": null,
    "raw_text": null,
    "confidence": null,
    "duration_ms": null,
    "error_message": null,
    "created_at": "2026-07-10T12:00:00",
    "started_at": "2026-07-10T12:01:00",
    "finished_at": null,
    "updated_at": "2026-07-10T12:02:00"
  }
}
```

## Submit OCR Result

### POST /api/ocr/jobs/{id}/result

Marks the OCR job `succeeded`, records the OCR output fields, writes `finished_at`, and copies `raw_text` to the related `Question.raw_text`. It does not modify `Question.corrected_text`.

Request body:

```json
{
  "raw_json": {
    "lines": [
      {"text": "2x + 3 = 7", "confidence": 0.98}
    ]
  },
  "raw_text": "2x + 3 = 7",
  "model_name": "mock-ocr",
  "duration_ms": 1234,
  "confidence": 0.98
}
```

Example:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/ocr/jobs/1/result" -H "X-Worker-Token: change-me" -H "Content-Type: application/json" -d "{\"raw_json\":{\"lines\":[{\"text\":\"2x + 3 = 7\",\"confidence\":0.98}]},\"raw_text\":\"2x + 3 = 7\",\"model_name\":\"mock-ocr\",\"duration_ms\":1234,\"confidence\":0.98}"
```

Response:

```json
{
  "job": {
    "ocr_job_id": 1,
    "question_id": 1,
    "asset_id": 1,
    "file_path": "data/uploads/2026/07/10/example.jpg",
    "status": "succeeded",
    "worker_name": "windows-laptop-01",
    "model_name": "mock-ocr",
    "raw_json": "{\"lines\":[{\"text\":\"2x + 3 = 7\",\"confidence\":0.98}]}",
    "raw_text": "2x + 3 = 7",
    "confidence": 0.98,
    "duration_ms": 1234,
    "error_message": null,
    "created_at": "2026-07-10T12:00:00",
    "started_at": "2026-07-10T12:01:00",
    "finished_at": "2026-07-10T12:03:00",
    "updated_at": "2026-07-10T12:03:00"
  }
}
```

## Fail OCR Job

### POST /api/ocr/jobs/{id}/fail

Marks the OCR job `failed`, writes `finished_at`, and stores `error_message`.

Request body:

```json
{
  "error_message": "OCR engine timed out"
}
```

Example:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/ocr/jobs/1/fail" -H "X-Worker-Token: change-me" -H "Content-Type: application/json" -d "{\"error_message\":\"OCR engine timed out\"}"
```

Response:

```json
{
  "job": {
    "ocr_job_id": 1,
    "question_id": 1,
    "asset_id": 1,
    "file_path": "data/uploads/2026/07/10/example.jpg",
    "status": "failed",
    "worker_name": "windows-laptop-01",
    "model_name": null,
    "raw_json": null,
    "raw_text": null,
    "confidence": null,
    "duration_ms": null,
    "error_message": "OCR engine timed out",
    "created_at": "2026-07-10T12:00:00",
    "started_at": "2026-07-10T12:01:00",
    "finished_at": "2026-07-10T12:03:00",
    "updated_at": "2026-07-10T12:03:00"
  }
}
```

## Retry OCR Job

### POST /api/ocr/jobs/{id}/retry

Moves a failed OCR job back to `pending`. It clears `error_message`, `started_at`, and `finished_at`. The original OCR job row is kept.

Example:

```powershell
curl.exe -X POST -H "X-Worker-Token: change-me" "http://127.0.0.1:8000/api/ocr/jobs/1/retry"
```

Response:

```json
{
  "job": {
    "ocr_job_id": 1,
    "question_id": 1,
    "asset_id": 1,
    "file_path": "data/uploads/2026/07/10/example.jpg",
    "status": "pending",
    "worker_name": "windows-laptop-01",
    "model_name": null,
    "raw_json": null,
    "raw_text": null,
    "confidence": null,
    "duration_ms": null,
    "error_message": null,
    "created_at": "2026-07-10T12:00:00",
    "started_at": null,
    "finished_at": null,
    "updated_at": "2026-07-10T12:04:00"
  }
}
```

Calling retry on a job that is not `failed` returns HTTP 409.

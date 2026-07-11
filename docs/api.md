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

## Web App

### GET /app

Serves the minimal browser/PWA workflow for upload, browsing, detail viewing, and correction.

Static frontend assets are served under:

```text
/app/static/
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
- no image binary data stored in SQLite

## Browse Questions

### GET /api/questions

Returns a paginated list of questions for the Web/PWA.

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
## Mistake Tags

### GET /api/mistake-tags

Lists reusable mistake tags. Optional query parameters are `q`, `limit`, and `offset`.

### PUT /api/questions/{question_id}/mistake-tags

Replaces all mistake tags assigned to a question. Missing names are created automatically. Names are trimmed, matched case-insensitively, de-duplicated, and limited to 20 tags per question.

Request body:

```json
{
  "names": ["calculation error", "concept unclear"]
}
```

The response contains the updated question detail, including `mistake_tags`.

## Review Scheduling

### POST /api/questions/{question_id}/reviews

Creates one pending review for a question. A question can have only one incomplete review at a time.

Request body:

```json
{
  "due_at": "2026-07-12T09:00:00Z"
}
```

Returns HTTP 409 when the question already has a pending review.

### GET /api/reviews/due

Lists incomplete reviews due on or before `before`. When `before` is omitted, the current UTC time is used. The response embeds a lightweight question summary for each review.

Query parameters:

- `before`: optional ISO 8601 datetime
- `limit`: default `50`, maximum `200`
- `offset`: default `0`

### POST /api/reviews/{review_id}/complete

Completes a pending review. Valid results are `again`, `hard`, `good`, and `easy`. Supplying `next_due_at` also creates the next pending review for the same question.

Request body:

```json
{
  "result": "good",
  "next_due_at": "2026-07-19T09:00:00Z"
}
```

Question summaries now include `mistake_tags` and `next_review`. Question detail responses also include the full `reviews` history.

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

## Knowledge Points

### `GET /api/knowledge-points`

Lists reusable knowledge points. Optional query parameters: `subject`, `parent_id`, `q`, `limit`, and `offset`.

### `POST /api/knowledge-points`

Creates a knowledge point.

```json
{
  "name": "Quadratic Functions",
  "subject": "Mathematics",
  "parent_id": 1
}
```

Names are unique case-insensitively within one subject. A child and its parent must use the same subject.

### `PUT /api/questions/{question_id}/knowledge-points`

Replaces all knowledge points assigned to one question.

```json
{
  "ids": [1, 2]
}
```

Duplicate IDs are ignored. A question can have at most 30 knowledge points. Deletion is intentionally not included in the MVP because points may already be shared by questions.

## Review Statistics

### `GET /api/reviews/stats`

Returns lightweight UTC-based review statistics:

- `due_count`: pending reviews due as of the requested time
- `completed_today`: reviews completed during the current UTC day
- `completed_seven_days`: reviews completed during the current UTC day and previous six days
- `result_counts_seven_days`: counts for `again`, `hard`, `good`, and `easy`
- `mastered_rate_seven_days`: `(good + easy) / completed_seven_days`, or `null` when no reviews were completed

An optional `now` datetime is supported for deterministic reporting and tests. Normal clients should omit it.

## Question Statistics

### `GET /api/questions/stats`

Returns lightweight question-library aggregates:

- `total_questions`
- `status_counts`
- `subject_counts`, with blank subjects grouped as `Uncategorized`
- `top_knowledge_points`, ordered by assigned question count

The optional `knowledge_limit` query parameter defaults to 10 and is limited to 50. Aggregates are calculated by the database rather than loading every question into application memory.

## Question Archive Workflow

### `POST /api/questions/{question_id}/archive`

Marks a question as `archived`. The operation is idempotent and does not delete records, images, OCR output, tags, knowledge points, or review history.

### `POST /api/questions/{question_id}/restore`

Restores an archived question to `corrected`. Returns HTTP 409 when the question is not archived.

## Review History

### `GET /api/reviews/history`

Lists completed reviews newest first. Optional filters:

- `result`: `again`, `hard`, `good`, or `easy`
- `question_id`
- `reviewed_from`
- `reviewed_to`
- `limit` and `offset`

Each item includes a question summary. Invalid result values or reversed date ranges return HTTP 400.

## Detailed Health

### `GET /health/details`

Returns deployment-oriented checks while keeping `GET /health` unchanged for simple liveness probes:

- database connectivity
- upload directory path and writability
- total, used, and free disk bytes
- configured minimum free disk threshold

Set `MIN_FREE_DISK_BYTES` to override the default 1 GiB threshold. The response status is `degraded` when any detailed check fails.

## Question Export

### `GET /api/questions/{question_id}/export`

Downloads one question using `format=json` or `format=markdown`.

JSON export includes a versioned envelope and the full question detail response, including metadata, corrected text, OCR text, tags, knowledge points, assets, OCR jobs, and review records. Image bytes are not embedded.

Markdown export contains readable metadata, corrected text, OCR text, knowledge points, mistake tags, and review history. Response filenames are sanitized from the question title.

## Filtered Question Collection Export

### `GET /api/questions/export`

Downloads a filtered question collection using `format=json` or `format=markdown`. It accepts the same `status`, `subject`, and `q` filters as the question list. `limit` defaults to 500 and cannot exceed 500 to protect the low-resource server.

The JSON envelope reports applied filters, total matching questions, exported count, and full question detail records. Markdown contains a collection heading followed by one readable section per question. Images are not embedded.

### `POST /api/questions/import`

Uploads a `.json` file in `wrongbook-question` v1 or `wrongbook-question-collection` v1 format. A file may contain at most 500 questions and may not exceed 5 MiB. Import always creates new questions, reuses matching knowledge points and mistake tags, and ignores old IDs, images, OCR jobs, review history, and original timestamps. Any invalid question rolls back the entire import.

### `POST /api/questions/{question_id}/ocr-jobs`

Creates a new pending OCR job from the question's first stored image. It keeps previous OCR jobs as history and never clears `corrected_text`. The endpoint returns `409` when the question has no image or already has a pending/running OCR job.

## Formula OCR crop

`POST /api/questions/{question_id}/formula-ocr` accepts one tightly cropped image up to 5 MiB. It creates a `QuestionAsset` with `asset_type=formula_crop` and an OCR job with `engine_name=formula`. Only one pending or running formula job is allowed per question. Formula result submission updates only the OCR job; it never changes the question `raw_text`, `corrected_text`, or status.

## Sources and chapters

- `GET /api/sources` lists sources with their chapters.
- `POST /api/sources` creates a source.
- `POST /api/chapters` creates a chapter and validates that its optional parent belongs to the same source.
- `PATCH /api/questions/{question_id}` accepts `source_id`, `chapter_id`, `source_page`, `answer_text`, `solution_text`, `personal_solution`, `wrong_answer`, `mistake_analysis`, `key_steps`, and `notes`.

Assigning a chapter automatically assigns its source. A chapter from a different selected source is rejected.
## Question organization filters and bulk update

`GET /api/questions` accepts optional `source_id` and `chapter_id` query parameters. `POST /api/questions/bulk-update` updates up to 200 selected questions with a source, chapter, or status. `POST /api/questions/manual` accepts optional `source_id`, `chapter_id`, and `source_page` multipart fields.
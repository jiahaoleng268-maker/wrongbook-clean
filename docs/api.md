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
- no OCR Worker
- no PaddleOCR
- no frontend
- no image binary data stored in SQLite

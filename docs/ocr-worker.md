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

The next OCR-related step should be to design the server-side OCR job table and API, then implement a mock worker. PaddleOCR installation and model wiring should happen only after the API and mock worker flow are stable.

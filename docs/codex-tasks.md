# Codex Task Plan

This file tracks completed work and the recommended next tasks for AI-assisted development.

## Completed

- GitHub repository synchronized
- Windows local clone created
- minimal FastAPI backend created
- `GET /` endpoint added
- `GET /health` endpoint added
- backend migrated to `apps/api`
- current backend entrypoint is `apps.api.app.main:app`
- project documentation and `AGENTS.md` created
- SQLite data model and database initialization logic added
- image upload API added at `POST /api/questions/upload`
- OCR Job Worker interface added
- Worker token authentication added
- safe uploaded asset file endpoint added at `GET /api/assets/{asset_id}/file`
- mock OCR Worker loop added
- focused integration tests added for upload, asset download, OCR jobs, and mock Worker flow
- selectable OCR engine layer added to the Worker
- `OCR_ENGINE=paddle` placeholder mode added with clear failed-job setup errors
- PaddlePaddle GPU and PaddleOCR installed and verified on the Windows laptop
- real local PaddleOCR engine wired behind `OCR_ENGINE=paddle`

## Current Task

- verify full upload-to-real-PaddleOCR Worker flow against the local backend
- keep `OCR_ENGINE=mock` as the default for routine development
- keep the 2c2g server free of OCR/model workloads

## Next Tasks

Recommended order:

1. run end-to-end OCR Worker verification with `OCR_ENGINE=paddle`
2. add UI/API endpoints for browsing questions and OCR text
3. Vue 3 + Vite frontend

## Task Boundaries

Keep each task small.

Do not combine upload API, OCR worker, and frontend work in one change.

The first version should avoid:

- Redis
- Celery
- PostgreSQL
- MinIO
- Elasticsearch
- Kubernetes
- server-side OCR
- server-side large language models

## Suggested Next Codex Prompt

```text
Please run an end-to-end local verification with OCR_ENGINE=paddle: start the API, upload a test image, run the Worker once in paddle mode, confirm the OCR job becomes succeeded with real raw_text, and do not commit model files, uploaded images, databases, or virtual environments.
```

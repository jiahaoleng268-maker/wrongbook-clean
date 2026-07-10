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

## Current Task

- prepare PaddleOCR Worker mode behind a selectable OCR engine
- keep mock mode as the default local verification path
- do not install PaddleOCR on the server

## Next Tasks

Recommended order:

1. PaddleOCR Worker mode
2. Vue 3 + Vite frontend
3. review scheduling and mistake tagging APIs

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
Please add a selectable OCR engine layer for the WrongBook Worker. Keep mock mode as the default, add a PaddleOCR placeholder mode that fails jobs with a clear dependency error when PaddleOCR is not installed, do not install PaddleOCR yet, do not create a frontend, and keep server-side OCR disabled.
```

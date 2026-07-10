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

## Current Task

- implement mock OCR Worker minimum loop
- poll OCR jobs from the backend
- fetch uploaded assets through the backend
- submit mock OCR results or failures

## Next Tasks

Recommended order:

1. add focused automated tests for OCR job and mock Worker flow
2. PaddleOCR Worker mode
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
Please add focused automated tests for the WrongBook OCR job API and mock Worker flow. Do not install PaddleOCR, do not create a frontend, and keep the server lightweight.
```

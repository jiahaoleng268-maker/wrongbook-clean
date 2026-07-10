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

## Current Task

- verify the image upload API
- confirm uploaded files are ignored by Git
- confirm uploaded records create `Question`, `QuestionAsset`, and pending `OCRJob` rows

## Next Tasks

Recommended order:

1. OCR job table API
2. OCR Worker mock mode
3. PaddleOCR Worker mode
4. Vue 3 + Vite frontend

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
Please implement the first OCR job API for WrongBook using the existing FastAPI app and SQLite data model. Do not implement OCR processing, do not install PaddleOCR, do not create a frontend, and include verification steps.
```

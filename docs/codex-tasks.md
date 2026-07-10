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

## Next Tasks

Recommended order:

1. image upload API
2. OCR job table API
3. OCR Worker mock mode
4. PaddleOCR Worker mode
5. Vue 3 + Vite frontend

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
Please implement the first image upload API for WrongBook using the existing FastAPI app and SQLite data model. Store image files on disk, store only paths in SQLite, do not implement OCR processing, do not create a frontend, and include verification steps.
```

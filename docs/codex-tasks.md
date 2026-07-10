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

## Current Documentation Task

- create and update project documentation
- create `AGENTS.md` for Continue/Codex development rules
- document product scope
- document architecture
- document OCR Worker design
- document local development workflow

## Next Tasks

Recommended order:

1. SQLite data model
2. image upload API
3. OCR job table and API
4. OCR Worker mock mode
5. PaddleOCR Worker mode
6. Vue 3 + Vite frontend

## Task Boundaries

Keep each task small.

Do not combine database schema, upload API, OCR worker, and frontend work in one change.

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
Please implement the first SQLite data model for WrongBook in the existing FastAPI backend. Keep it lightweight, use SQLite only, do not implement OCR, do not create a frontend, and include verification steps.
```

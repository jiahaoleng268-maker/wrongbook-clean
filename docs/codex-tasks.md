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
- question browse, detail, and edit APIs added
- minimal static Web/PWA scaffold added for upload, browsing, detail, and correction

## Current Task

- add review scheduling and mistake tagging APIs
- keep the first review workflow simple and API-first
- keep the 2c2g server free of OCR/model workloads

## Next Tasks

Recommended order:

1. add review scheduling and mistake tagging APIs
2. show review and tag data in the Web app
3. improve OCR text cleanup for math/chinese output

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
Please add simple review scheduling and mistake tagging APIs for WrongBook. Keep the data model lightweight, add focused integration tests, and do not add server-side OCR or heavy infrastructure.
```

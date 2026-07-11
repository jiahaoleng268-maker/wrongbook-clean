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

## Current Task

- prepare a small frontend/PWA-facing question workflow
- keep API-first development before building the full interface
- keep the 2c2g server free of OCR/model workloads

## Next Tasks

Recommended order:

1. add minimal frontend/PWA scaffold for upload and question browsing
2. add review scheduling and mistake tagging APIs
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
Please add a minimal frontend/PWA scaffold for WrongBook that can upload an image, list questions, open question details, and edit corrected_text. Keep it lightweight, do not add heavy infrastructure, and keep OCR/model workloads outside the server.
```

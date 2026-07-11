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

## Current Task

- prepare real PaddleOCR installation and model wiring on the Windows laptop
- keep `OCR_ENGINE=mock` as the default until PaddleOCR is verified locally
- keep the 2c2g server free of OCR/model workloads

## Next Tasks

Recommended order:

1. install and verify PaddleOCR locally on the Windows laptop
2. wire the real PaddleOCR engine behind `OCR_ENGINE=paddle`
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
Please prepare the next PaddleOCR integration step for the Windows laptop only. First verify the correct PaddleOCR/PaddlePaddle installation commands for this machine, keep OCR_ENGINE=mock as the default, and do not put PaddleOCR or model files on the server or into Git.
```

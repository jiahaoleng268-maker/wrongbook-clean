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
- mistake tagging and review scheduling APIs added
- Web/PWA mistake tag editing, review scheduling, and due-review completion added
- conservative PaddleOCR text cleanup added for mojibake, full-width characters, and invisible controls
- hierarchical knowledge point list, create, and question assignment APIs added
- Web/PWA knowledge point creation and question assignment added
- real RTX 5070 PaddleOCR evaluation documented for a photographed calculus question
- SQLite and uploaded-image backup, verification, and safe restore workflow added
- lightweight current-day and seven-day review statistics added to the API and Web/PWA
- Linux cron backup scheduling, verification, and retention guidance added
- question status, subject, and knowledge-point statistics added to the API and Web/PWA
- reversible question archive/restore workflow and filtered review history added
- question and review-history pagination plus detailed deployment health checks added
- versioned JSON and readable Markdown question exports added
- skip navigation, live status regions, visible focus, and keyboard shortcuts added

## Current Task

- show review and mistake tag data in the Web app
- keep the first review workflow simple and mobile-friendly
- keep the 2c2g server free of OCR/model workloads

## Next Tasks

Recommended order:

1. show review and tag data in the Web app
2. improve OCR text cleanup for math/chinese output
3. add knowledge point management APIs

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
Please show mistake tags and upcoming review information in the WrongBook Web app. Add simple controls for replacing tags, scheduling a review, and completing due reviews. Keep the interface mobile-friendly and lightweight.
```

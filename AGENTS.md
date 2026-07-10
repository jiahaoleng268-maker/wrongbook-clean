# AGENTS.md

This file defines the working rules for Continue, Codex, and other AI coding agents working on WrongBook.

## Project Shape

WrongBook is a personal wrong-question collection and review system. It should stay lightweight in the first version.

Current backend entrypoint:

```powershell
python -m uvicorn apps.api.app.main:app --reload
```

Current backend endpoints:

- `GET /`
- `GET /health`

## Hard Constraints

- The production server is low-resource: 2 CPU cores, 2 GB RAM, 50 GB disk.
- The server must not run OCR.
- The server must not run large language models.
- PaddleOCR Worker runs on the Windows laptop, not on the server.
- Do not introduce Redis, Celery, PostgreSQL, MinIO, Elasticsearch, or Kubernetes in the first version.
- Do not create a frontend until the API foundations are ready.
- When the frontend is created, build a useful tool interface, not a marketing landing page.

## Data Safety

Never commit:

- secrets or real `.env` files
- SQLite databases
- uploaded images
- downloaded images
- runtime files
- logs
- PaddleOCR models
- backups
- virtual environments

Keep sample configuration in `.env.example` only.

## Implementation Rules

- Keep changes small and focused.
- Prefer the existing project structure and dependencies.
- Do not add new dependencies unless the task explicitly requires them.
- Do not introduce database, OCR, worker, or frontend code while doing documentation-only tasks.
- Keep the first version simple: FastAPI, SQLite, local files, and a polling OCR worker are enough.
- Server-side OCR job state should be designed to work with a simple polling worker.
- Windows-specific worker paths should be documented before they are automated.

## Verification Rules

Every feature change must include a verification step.

Examples:

- Start the API with `python -m uvicorn apps.api.app.main:app --reload`.
- Check `GET /`.
- Check `GET /health`.
- For future upload APIs, verify file creation and database rows.
- For future OCR job APIs, verify job creation, polling, status update, and result submission.

If a command cannot be run in the current environment, explain what was not run and why.

## Documentation Rules

- Update README when startup commands or project structure change.
- Update docs when architecture, worker behavior, data paths, or development workflow change.
- Keep docs practical and current.

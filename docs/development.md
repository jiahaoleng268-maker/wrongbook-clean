# Development

This document describes local development on Windows.

## Repository

```text
D:\Code\WB\wrongbook
```

## Start Backend Locally

Open PowerShell:

```powershell
cd D:\Code\WB\wrongbook
.\.venv\Scripts\Activate.ps1
pip install -r apps\api\requirements.txt
python -m uvicorn apps.api.app.main:app --reload
```

The API should be available at:

```text
http://127.0.0.1:8000
```

Open the local Web app at:

```text
http://127.0.0.1:8000/app
```

The Web app is served by FastAPI from `apps/api/app/static`. No Node.js or frontend build step is required for the MVP.

## Initialize Database

The default SQLite database URL is:

```env
DATABASE_URL=sqlite:///./data/app.db
```

Create the SQLite tables manually with:

```powershell
python -m apps.api.app.init_db
```

The app also creates tables during FastAPI startup. Do not commit `data/app.db`.

## Test Current Endpoints

PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-WebRequest http://127.0.0.1:8000/app
```

Expected results:

```json
{"message":"WrongBook API is running"}
```

```json
{"status":"ok"}
```

Curl:

```powershell
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/health
```

## Run Automated Tests

The current tests start a temporary API server with an isolated SQLite database and upload directory. They also verify the static Web app shell. They do not use `data/app.db`, do not use `data/uploads`, and do not require PaddleOCR.

PowerShell:

```powershell
cd D:\Code\WB\wrongbook
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests
```

## Git Safety

Before committing, check:

```powershell
git status --short
git status --short --ignored
```

Do not commit:

- `.venv/`
- `.env`
- SQLite database files
- uploaded images
- downloaded images
- logs
- runtime files
- PaddleOCR models
- backups

Documentation-only tasks should not modify backend business code.

## Dependency Rule

Use:

```powershell
pip install -r apps\api\requirements.txt
```

Do not introduce new dependencies unless a task explicitly requires them.

## Web Review Workflow

The no-build Web/PWA supports editing comma-separated mistake tags, scheduling one pending review per question, and completing due reviews from the **今日复习** section.

Review results create the next review with fixed MVP intervals:

- `again`: 10 minutes
- `hard`: 1 day
- `good`: 3 days
- `easy`: 7 days

Manual verification: upload a question, save tags, schedule a due time, refresh, then complete the review and confirm the next due time is shown.

## Web Knowledge Point Workflow

Question details show all reusable knowledge points as mobile-friendly checkboxes. Saving the question replaces its knowledge point assignments. A new knowledge point can be created inline with an optional subject; when the subject input is empty, the current question subject is used. Newly created points are selected automatically but are not assigned until the question is saved.

## Review Statistics

The **今日复习** panel shows current due reviews, today's completed count, seven-day completed count, seven-day mastered rate, and the four result counts. Statistics use UTC day boundaries to match server-side review timestamps and refresh after scheduling or completing a review.

## Question Library Statistics

The Web/PWA **题库概览** section displays total questions, status counts, subject counts, and the most-used knowledge points. It refreshes after question changes and when the main refresh button is used.

## Archive and Review History

Question details provide explicit archive and restore actions. Archiving is reversible and never deletes images or related learning data. The **复习历史** section shows completed reviews and filters by result and date range; selecting a history row opens the related question.

## Pagination

Question results and completed review history use 20-item pages with previous/next controls. Changing question search/status filters or review-history filters resets the related list to the first page.

## Export and Keyboard Access

Question details provide JSON and Markdown download buttons. JSON is intended for structured interchange; Markdown is intended for notes and manual archives. Images remain separate uploaded assets.

Keyboard shortcuts:

- `/`: focus question search when not editing a field
- `Ctrl+S` or `Cmd+S`: save the selected question
- `R`: refresh lists and statistics when not editing a field

The page includes a skip link, visible focus outlines, polite live regions for asynchronous status messages, and reduced-motion support.

## Filtered Collection Export

The question-list panel can export the current search and status filter as JSON or Markdown. Exports include all matching questions up to the server-side 500-question safety limit, not only the visible page.

## JSON ????

???????????? JSON????????????????????????????? ID????OCR ?????????????

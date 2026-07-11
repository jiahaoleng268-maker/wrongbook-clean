# Data Model

WrongBook uses SQLite for the first version. SQLAlchemy defines the tables and creates them during application startup or through the manual initialization command.

Default database URL:

```env
DATABASE_URL=sqlite:///./data/app.db
```

Manual initialization command:

```powershell
python -m apps.api.app.init_db
```

The database file is stored at `data/app.db` by default and must not be committed to Git. Only `data/.gitkeep` should be committed as the empty directory placeholder.

## Tables

### questions

Stores the main wrong-question record.

Important fields:

- `subject`: subject name, such as math or physics
- `title`: short display title
- `raw_text`: original OCR text
- `corrected_text`: manually corrected text
- `question_type`: type of question
- `difficulty`: difficulty label
- `source`: book, exam, worksheet, or other source
- `status`: `draft`, `recognized`, `corrected`, or `archived`
- `created_at`, `updated_at`: timestamps

### question_assets

Stores files related to a question. It stores file paths only, not image binary data.

Important fields:

- `question_id`: related question
- `file_path`: local or server-side file path
- `asset_type`: `original`, `crop`, `answer`, `explanation`, or `formula`
- `width`, `height`: optional image dimensions
- `sha256`: optional file hash for duplicate detection

### ocr_jobs

Stores OCR task state and OCR results. The server manages the job state, but OCR runs on the Windows laptop worker.

Important fields:

- `question_id`: related question
- `asset_id`: related asset, usually an image
- `status`: `pending`, `running`, `succeeded`, or `failed`
- `model_name`: OCR model name reported by the worker
- `worker_name`: worker name that processed the job
- `raw_json`: original OCR JSON as text
- `raw_text`: extracted OCR text
- `confidence`: optional OCR confidence score
- `duration_ms`: processing duration
- `error_message`: failure reason when status is `failed`
- `created_at`, `started_at`, `finished_at`, `updated_at`: timestamps

### knowledge_points

Stores subject knowledge points and supports parent-child hierarchy.

Important fields:

- `subject`: subject name
- `name`: knowledge point name
- `parent_id`: optional parent knowledge point

### mistake_tags

Stores mistake reason tags, such as:

- concept unclear
- calculation error
- misread question
- formula forgotten
- non-standard steps

### reviews

Stores scheduled review records for spaced review.

Important fields:

- `question_id`: related question
- `due_at`: planned review time
- `reviewed_at`: actual review time
- `result`: `again`, `hard`, `good`, or `easy`
- `next_due_at`: next planned review time

### attempts

Stores practice attempts for a question.

Important fields:

- `question_id`: related question
- `answer_text`: submitted answer text
- `is_correct`: whether the attempt was correct
- `duration_seconds`: time spent on the attempt
- `created_at`: attempt time

### question_knowledge_points

Many-to-many relationship table between `questions` and `knowledge_points`.

### question_mistake_tags

Many-to-many relationship table between `questions` and `mistake_tags`.

## Current Scope

The current application uses these tables for image upload, OCR jobs, reusable hierarchical knowledge points, mistake tags, and review scheduling. OCR processing still runs only in the separate Windows Worker.

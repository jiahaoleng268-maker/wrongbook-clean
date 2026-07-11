# Backup and Restore

WrongBook backups use one ZIP file containing a consistent SQLite snapshot, uploaded images, and a SHA-256 manifest. The script uses only the Python standard library.

## Create a Backup

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\backup_restore.py backup
```

The default output is a timestamped file under `backups/`. That directory is ignored by Git.

Custom paths:

```powershell
.\.venv\Scripts\python.exe scripts\backup_restore.py backup `
  --database-url "sqlite:///./data/app.db" `
  --uploads-dir data\uploads `
  --output backups\wrongbook-manual.zip
```

The SQLite online backup API creates a consistent database snapshot while the application is running. Uploaded files added during the backup may appear in the next backup, so schedule backups during low activity when possible.

## Verify a Backup

```powershell
.\.venv\Scripts\python.exe scripts\backup_restore.py verify backups\wrongbook-manual.zip
```

Verification rejects missing files, additional unlisted files, unsafe archive paths, and SHA-256 or size mismatches.

## Restore a Backup

Stop the FastAPI process before restoring so it does not keep the SQLite file open or write during replacement.

Restore into an empty target:

```powershell
.\.venv\Scripts\python.exe scripts\backup_restore.py restore backups\wrongbook-manual.zip
```

The command refuses to overwrite an existing database or uploads directory. To replace existing data safely:

```powershell
.\.venv\Scripts\python.exe scripts\backup_restore.py restore backups\wrongbook-manual.zip --replace
```

Before replacement, current data is moved into a timestamped `pre-restore-*` directory beside the database. Keep that directory until the restored application has been checked.

## Post-Restore Check

Start the API and verify:

```powershell
.\.venv\Scripts\python.exe -m uvicorn apps.api.app.main:app
Invoke-RestMethod http://127.0.0.1:8000/health
```

Open `/app`, confirm question records and images, then run a new backup after validation.

## Safety Rules

- Never commit backup ZIP files or `pre-restore-*` directories.
- Copy important backup files to storage outside the server.
- Verify backups periodically; an unverified backup is not sufficient.
- Do not restore while the API is running.
- The script intentionally supports SQLite only and does not add external backup services.
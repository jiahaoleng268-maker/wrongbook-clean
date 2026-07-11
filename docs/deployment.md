# Deployment Operations

WrongBook is designed for a small Linux server with FastAPI, SQLite, local uploaded files, and no server-side OCR.

## Daily Backup Schedule

Use the operating system scheduler instead of adding Celery, Redis, or another service. Run backups during a low-activity period, for example 03:15 server local time.

Example crontab entry:

```cron
15 3 * * * cd /opt/wrongbook && /opt/wrongbook/.venv/bin/python scripts/backup_restore.py backup >> /opt/wrongbook/logs/backup.log 2>&1
```

Create the ignored runtime directories before enabling the schedule:

```bash
mkdir -p /opt/wrongbook/backups /opt/wrongbook/logs
```

## Verification Schedule

Creating a ZIP is not enough. Verify the newest backup after creation. A small shell wrapper can run both commands and fail the scheduled job when verification fails:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /opt/wrongbook
backup="backups/wrongbook-$(date +%Y%m%d-%H%M%S).zip"
.venv/bin/python scripts/backup_restore.py backup --output "$backup"
.venv/bin/python scripts/backup_restore.py verify "$backup"
```

Schedule the wrapper instead of the direct backup command after testing it manually.

## Retention

For a personal deployment, retain:

- 7 daily backups
- 4 weekly backups stored outside the server
- 3 monthly backups stored outside the server

Do not automatically delete the only known-good backup. First copy verified files to another machine, NAS, or encrypted cloud storage. The built-in script intentionally does not delete backups.

Example cleanup command after off-server copies are confirmed:

```bash
find /opt/wrongbook/backups -type f -name 'wrongbook-*.zip' -mtime +7 -print
```

Review the printed list before adding `-delete` to an operational script.

## Restore Drill

At least monthly, restore one verified backup into a temporary directory or non-production machine and confirm:

- SQLite integrity passes
- question rows are readable
- uploaded images exist
- `/health` responds after startup
- `/app` displays questions and images

Never test restoration by overwriting the only production copy.

## Server Boundaries

- Keep PaddleOCR and GPU dependencies off the server.
- Keep backup ZIP files and logs out of Git.
- Restrict backup file permissions because the archive contains all questions and images.
- Monitor free disk space; local uploads and retained backups share the 50 GB disk.
## Health and Disk Monitoring

Use `GET /health` for a lightweight process liveness probe and `GET /health/details` for operational checks.

```bash
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/health/details
```

The detailed endpoint checks database connectivity, upload-path writability, and available disk space. The default minimum is 1 GiB. Configure a larger threshold for the 50 GB server when desired:

```env
MIN_FREE_DISK_BYTES=5368709120
```

Alert when the detailed response reports `degraded`, when disk free space drops below the chosen threshold, or when the backup schedule stops producing verified archives.

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import tempfile
from urllib.parse import urlparse
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile


MANIFEST_NAME = "manifest.json"
DATABASE_ARCHIVE_PATH = "database/app.db"
UPLOADS_ARCHIVE_PREFIX = "uploads"
BACKUP_FORMAT_VERSION = 1


def sqlite_path_from_url(database_url: str) -> Path:
    parsed = urlparse(database_url)
    if parsed.scheme != "sqlite":
        raise ValueError("Backup supports SQLite database URLs only.")
    if database_url == "sqlite:///:memory:":
        raise ValueError("Cannot back up an in-memory SQLite database.")
    raw_path = parsed.path
    if raw_path.startswith("/") and not raw_path.startswith("//"):
        raw_path = raw_path[1:]
    path = Path(raw_path)
    return path if path.is_absolute() else Path.cwd() / path


def file_digest(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def archive_member_digest(archive: ZipFile, name: str) -> tuple[str, int]:
    digest = sha256()
    size = 0
    with archive.open(name) as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def safe_member_name(name: str) -> str:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"Unsafe archive path: {name!r}")
    return path.as_posix()


def create_sqlite_snapshot(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"SQLite database not found: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_db = sqlite3.connect(source)
    destination_db = sqlite3.connect(destination)
    try:
        source_db.backup(destination_db)
    finally:
        destination_db.close()
        source_db.close()
    snapshot_db = sqlite3.connect(destination)
    try:
        result = snapshot_db.execute("PRAGMA integrity_check").fetchone()
    finally:
        snapshot_db.close()
    if not result or result[0] != "ok":
        raise ValueError(f"SQLite integrity check failed: {result}")


def create_backup(database_path: Path, uploads_dir: Path, output_path: Path) -> dict:
    database_path = database_path.resolve()
    uploads_dir = uploads_dir.resolve()
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise FileExistsError(f"Backup already exists: {output_path}")

    with tempfile.TemporaryDirectory(prefix="wrongbook-backup-") as temp_name:
        snapshot = Path(temp_name) / "app.db"
        create_sqlite_snapshot(database_path, snapshot)
        files = [{
            "path": DATABASE_ARCHIVE_PATH,
            "sha256": file_digest(snapshot),
            "size": snapshot.stat().st_size,
        }]
        upload_files = []
        if uploads_dir.is_dir():
            upload_files = sorted(path for path in uploads_dir.rglob("*") if path.is_file())
            for path in upload_files:
                archive_path = PurePosixPath(UPLOADS_ARCHIVE_PREFIX) / PurePosixPath(path.relative_to(uploads_dir).as_posix())
                files.append({
                    "path": archive_path.as_posix(),
                    "sha256": file_digest(path),
                    "size": path.stat().st_size,
                })

        manifest = {
            "format": "wrongbook-backup",
            "version": BACKUP_FORMAT_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "database": DATABASE_ARCHIVE_PATH,
            "uploads_prefix": UPLOADS_ARCHIVE_PREFIX,
            "files": files,
        }
        temporary_output = output_path.with_name(f".{output_path.name}.{uuid4().hex}.tmp")
        try:
            with ZipFile(temporary_output, "w", compression=ZIP_DEFLATED) as archive:
                archive.write(snapshot, DATABASE_ARCHIVE_PATH)
                for path in upload_files:
                    archive_path = PurePosixPath(UPLOADS_ARCHIVE_PREFIX) / PurePosixPath(path.relative_to(uploads_dir).as_posix())
                    archive.write(path, archive_path.as_posix())
                archive.writestr(MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2))
            temporary_output.replace(output_path)
        finally:
            temporary_output.unlink(missing_ok=True)
    return manifest


def verify_backup(backup_path: Path) -> dict:
    backup_path = backup_path.resolve()
    with ZipFile(backup_path, "r") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Backup contains duplicate archive paths.")
        for name in names:
            safe_member_name(name)
        if MANIFEST_NAME not in names:
            raise ValueError("Backup manifest is missing.")
        manifest = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
        if manifest.get("format") != "wrongbook-backup" or manifest.get("version") != BACKUP_FORMAT_VERSION:
            raise ValueError("Unsupported WrongBook backup format.")
        expected_names = {MANIFEST_NAME}
        for entry in manifest.get("files", []):
            name = safe_member_name(entry["path"])
            expected_names.add(name)
            if name not in names:
                raise ValueError(f"Backup file is missing: {name}")
            digest, size = archive_member_digest(archive, name)
            if digest != entry.get("sha256") or size != entry.get("size"):
                raise ValueError(f"Backup checksum mismatch: {name}")
        if set(names) != expected_names:
            extra = sorted(set(names) - expected_names)
            raise ValueError(f"Backup contains unlisted files: {extra}")
        if manifest.get("database") != DATABASE_ARCHIVE_PATH:
            raise ValueError("Backup database path is invalid.")
    return manifest


def restore_backup(backup_path: Path, database_path: Path, uploads_dir: Path, replace: bool = False) -> dict:
    manifest = verify_backup(backup_path)
    database_path = database_path.resolve()
    uploads_dir = uploads_dir.resolve()
    existing = database_path.exists() or uploads_dir.exists()
    if existing and not replace:
        raise FileExistsError("Restore target already contains data. Use --replace to preserve and replace it.")

    database_path.parent.mkdir(parents=True, exist_ok=True)
    uploads_dir.parent.mkdir(parents=True, exist_ok=True)
    restore_root = Path(tempfile.mkdtemp(prefix="wrongbook-restore-", dir=database_path.parent))
    restored_database = restore_root / "app.db"
    restored_uploads = restore_root / "uploads"
    try:
        with ZipFile(backup_path, "r") as archive:
            restored_database.write_bytes(archive.read(DATABASE_ARCHIVE_PATH))
            for entry in manifest["files"]:
                name = entry["path"]
                if not name.startswith(f"{UPLOADS_ARCHIVE_PREFIX}/"):
                    continue
                relative = PurePosixPath(name).relative_to(UPLOADS_ARCHIVE_PREFIX)
                target = restored_uploads.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
        restored_db = sqlite3.connect(restored_database)
        try:
            result = restored_db.execute("PRAGMA integrity_check").fetchone()
        finally:
            restored_db.close()
        if not result or result[0] != "ok":
            raise ValueError(f"Restored SQLite integrity check failed: {result}")

        preserved = None
        if existing:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            preserved = database_path.parent / f"pre-restore-{timestamp}-{uuid4().hex[:8]}"
            preserved.mkdir()
            if database_path.exists():
                shutil.move(str(database_path), preserved / database_path.name)
            if uploads_dir.exists():
                shutil.move(str(uploads_dir), preserved / uploads_dir.name)

        shutil.move(str(restored_database), database_path)
        if restored_uploads.exists():
            shutil.move(str(restored_uploads), uploads_dir)
        else:
            uploads_dir.mkdir(parents=True, exist_ok=True)
        return {"manifest": manifest, "preserved_path": str(preserved) if preserved else None}
    finally:
        shutil.rmtree(restore_root, ignore_errors=True)


def default_backup_name() -> str:
    return f"wrongbook-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backup, verify, and restore WrongBook data.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup = subparsers.add_parser("backup")
    backup.add_argument("--database-url", default="sqlite:///./data/app.db")
    backup.add_argument("--uploads-dir", type=Path, default=Path("data/uploads"))
    backup.add_argument("--output", type=Path, default=None)

    verify = subparsers.add_parser("verify")
    verify.add_argument("backup_path", type=Path)

    restore = subparsers.add_parser("restore")
    restore.add_argument("backup_path", type=Path)
    restore.add_argument("--database-url", default="sqlite:///./data/app.db")
    restore.add_argument("--uploads-dir", type=Path, default=Path("data/uploads"))
    restore.add_argument("--replace", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "backup":
        output = args.output or Path("backups") / default_backup_name()
        manifest = create_backup(sqlite_path_from_url(args.database_url), args.uploads_dir, output)
        print(json.dumps({"backup": str(output.resolve()), "manifest": manifest}, ensure_ascii=False, indent=2))
    elif args.command == "verify":
        print(json.dumps(verify_backup(args.backup_path), ensure_ascii=False, indent=2))
    else:
        result = restore_backup(
            args.backup_path,
            sqlite_path_from_url(args.database_url),
            args.uploads_dir,
            replace=args.replace,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
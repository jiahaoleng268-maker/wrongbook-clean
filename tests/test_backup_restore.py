import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from zipfile import ZIP_DEFLATED, ZipFile

from scripts.backup_restore import create_backup, restore_backup, verify_backup


class BackupRestoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temp_dir.name)
        self.database = self.root / "source" / "app.db"
        self.uploads = self.root / "source" / "uploads"
        self.database.parent.mkdir(parents=True)
        self.uploads.mkdir(parents=True)
        with sqlite3.connect(self.database) as connection:
            connection.execute("CREATE TABLE questions (id INTEGER PRIMARY KEY, title TEXT)")
            connection.execute("INSERT INTO questions (title) VALUES (?)", ("calculus",))
            connection.commit()
        image = self.uploads / "2026" / "07" / "question.png"
        image.parent.mkdir(parents=True)
        image.write_bytes(b"question-image")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_backup_verify_and_restore_round_trip(self) -> None:
        backup = self.root / "backups" / "wrongbook.zip"
        manifest = create_backup(self.database, self.uploads, backup)
        self.assertEqual(len(manifest["files"]), 2)
        self.assertEqual(verify_backup(backup)["format"], "wrongbook-backup")

        restored_database = self.root / "restored" / "app.db"
        restored_uploads = self.root / "restored" / "uploads"
        result = restore_backup(backup, restored_database, restored_uploads)
        self.assertIsNone(result["preserved_path"])
        with sqlite3.connect(restored_database) as connection:
            title = connection.execute("SELECT title FROM questions").fetchone()[0]
        self.assertEqual(title, "calculus")
        self.assertEqual(
            (restored_uploads / "2026" / "07" / "question.png").read_bytes(),
            b"question-image",
        )

    def test_restore_refuses_overwrite_and_replace_preserves_existing_data(self) -> None:
        backup = self.root / "wrongbook.zip"
        create_backup(self.database, self.uploads, backup)
        target_database = self.root / "target" / "app.db"
        target_uploads = self.root / "target" / "uploads"
        target_database.parent.mkdir(parents=True)
        target_database.write_bytes(b"old database")
        target_uploads.mkdir()
        (target_uploads / "old.txt").write_text("old", encoding="utf-8")

        with self.assertRaises(FileExistsError):
            restore_backup(backup, target_database, target_uploads)

        result = restore_backup(backup, target_database, target_uploads, replace=True)
        preserved = Path(result["preserved_path"])
        self.assertEqual((preserved / "app.db").read_bytes(), b"old database")
        self.assertEqual((preserved / "uploads" / "old.txt").read_text(encoding="utf-8"), "old")

    def test_verify_rejects_checksum_tampering(self) -> None:
        backup = self.root / "wrongbook.zip"
        create_backup(self.database, self.uploads, backup)
        tampered = self.root / "tampered.zip"
        with ZipFile(backup, "r") as source, ZipFile(tampered, "w", compression=ZIP_DEFLATED) as target:
            for name in source.namelist():
                data = source.read(name)
                target.writestr(name, b"tampered" if name == "database/app.db" else data)
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            verify_backup(tampered)


if __name__ == "__main__":
    unittest.main()
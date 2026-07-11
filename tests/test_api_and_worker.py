import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKER_SCRIPT = REPO_ROOT / "apps" / "ocr-worker" / "mock_worker.py"
WORKER_TOKEN = "test-worker-token"
TEST_IMAGE_BYTES = b"fake png bytes for wrongbook tests"


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _multipart_body(field_name: str, filename: str, content_type: str, data: bytes) -> tuple[bytes, str]:
    boundary = f"----wrongbook-test-{time.time_ns()}"
    parts = [
        f"--{boundary}\r\n".encode("utf-8"),
        (
            f'Content-Disposition: form-data; name="{field_name}"; '
            f'filename="{filename}"\r\n'
        ).encode("utf-8"),
        f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
        data,
        b"\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


class WrongBookIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.test_root = Path(self.temp_dir.name)
        self.port = _find_free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"

        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{(self.test_root / 'app.db').as_posix()}"
        env["UPLOAD_DIR"] = (self.test_root / "uploads").as_posix()
        env["WORKER_TOKEN"] = WORKER_TOKEN
        env["PYTHONPATH"] = str(REPO_ROOT)

        self.server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "apps.api.app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
                "--log-level",
                "warning",
            ],
            cwd=REPO_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.env = env
        self._wait_for_health()

    def tearDown(self) -> None:
        self.server.terminate()
        try:
            self.server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.server.kill()
            self.server.wait(timeout=10)
        if self.server.stdout:
            self.server.stdout.close()
        if self.server.stderr:
            self.server.stderr.close()
        self.temp_dir.cleanup()

    def _wait_for_health(self) -> None:
        deadline = time.monotonic() + 15
        last_error = None
        while time.monotonic() < deadline:
            if self.server.poll() is not None:
                stdout, stderr = self.server.communicate(timeout=1)
                self.fail(f"API server exited early.\nstdout:\n{stdout}\nstderr:\n{stderr}")
            try:
                payload = self.request_json("GET", "/health")
                if payload == {"status": "ok"}:
                    return
            except Exception as exc:
                last_error = exc
                time.sleep(0.2)
        self.fail(f"API server did not become healthy: {last_error}")

    def request_json(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict:
        body = None
        request_headers = dict(headers or {})
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            request_headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers=request_headers,
            method=method,
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            response_body = response.read().decode("utf-8")
        return json.loads(response_body) if response_body else {}

    def request_text(self, method: str, path: str) -> tuple[str, str]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            method=method,
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            content_type = response.headers.get("Content-Type", "")
            response_body = response.read().decode("utf-8")
        return response_body, content_type

    def upload_image(self, filename: str = "sample.png") -> dict:
        body, content_type = _multipart_body(
            field_name="file",
            filename=filename,
            content_type="image/png",
            data=TEST_IMAGE_BYTES,
        )
        request = urllib.request.Request(
            f"{self.base_url}/api/questions/upload",
            data=body,
            headers={"Content-Type": content_type},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def worker_headers(self, worker_name: str = "test-worker") -> dict[str, str]:
        return {
            "X-Worker-Token": WORKER_TOKEN,
            "X-Worker-Name": worker_name,
        }

    def test_web_app_shell_and_static_assets(self) -> None:
        html, content_type = self.request_text("GET", "/app")
        self.assertIn("text/html", content_type)
        self.assertIn("WrongBook", html)
        self.assertIn('id="uploadForm"', html)

        fallback_html, _ = self.request_text("GET", "/app/questions/1")
        self.assertIn("WrongBook", fallback_html)

        css, css_content_type = self.request_text("GET", "/app/static/app.css")
        self.assertIn("text/css", css_content_type)
        self.assertIn(".app-shell", css)

        javascript, js_content_type = self.request_text("GET", "/app/static/app.js")
        self.assertIn("javascript", js_content_type)
        self.assertIn("/api/questions/upload", javascript)
        self.assertIn("serviceWorker", javascript)

        manifest = self.request_json("GET", "/app/static/manifest.webmanifest")
        self.assertEqual(manifest["short_name"], "WrongBook")
        self.assertEqual(manifest["start_url"], "/app")

        service_worker, sw_content_type = self.request_text("GET", "/app/service-worker.js")
        self.assertIn("javascript", sw_content_type)
        self.assertIn("CACHE_NAME", service_worker)

    def test_upload_asset_download_and_ocr_job_lifecycle(self) -> None:
        upload = self.upload_image()
        self.assertEqual(upload["status"], "pending")
        self.assertGreater(upload["question_id"], 0)
        self.assertGreater(upload["asset_id"], 0)
        self.assertGreater(upload["ocr_job_id"], 0)

        asset_request = urllib.request.Request(
            f"{self.base_url}/api/assets/{upload['asset_id']}/file",
            method="GET",
        )
        with urllib.request.urlopen(asset_request, timeout=10) as response:
            self.assertEqual(response.read(), TEST_IMAGE_BYTES)

        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request_json("GET", "/api/ocr/jobs/next")
        self.assertEqual(error.exception.code, 401)

        claimed = self.request_json(
            "GET",
            "/api/ocr/jobs/next",
            headers=self.worker_headers("lifecycle-worker"),
        )["job"]
        self.assertEqual(claimed["ocr_job_id"], upload["ocr_job_id"])
        self.assertEqual(claimed["status"], "running")
        self.assertEqual(claimed["worker_name"], "lifecycle-worker")

        result = self.request_json(
            "POST",
            f"/api/ocr/jobs/{claimed['ocr_job_id']}/result",
            payload={
                "raw_json": {"mock": True},
                "raw_text": "text from api test",
                "model_name": "test-model",
                "duration_ms": 12,
                "confidence": 0.95,
            },
            headers=self.worker_headers(),
        )["job"]
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["raw_text"], "text from api test")
        self.assertEqual(result["model_name"], "test-model")
        self.assertIsNone(result["error_message"])

        failed_upload = self.upload_image("failed.png")
        failed_job = self.request_json(
            "GET",
            "/api/ocr/jobs/next",
            headers=self.worker_headers(),
        )["job"]
        self.assertEqual(failed_job["ocr_job_id"], failed_upload["ocr_job_id"])

        failed = self.request_json(
            "POST",
            f"/api/ocr/jobs/{failed_job['ocr_job_id']}/fail",
            payload={"error_message": "mock failure"},
            headers=self.worker_headers(),
        )["job"]
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["error_message"], "mock failure")

        retried = self.request_json(
            "POST",
            f"/api/ocr/jobs/{failed_job['ocr_job_id']}/retry",
            headers=self.worker_headers(),
        )["job"]
        self.assertEqual(retried["status"], "pending")
        self.assertIsNone(retried["error_message"])
        self.assertIsNone(retried["started_at"])
        self.assertIsNone(retried["finished_at"])

    def test_question_browse_detail_and_update_api(self) -> None:
        upload = self.upload_image("browse.png")
        job = self.request_json(
            "GET",
            "/api/ocr/jobs/next",
            headers=self.worker_headers("question-api-worker"),
        )["job"]
        self.assertEqual(job["ocr_job_id"], upload["ocr_job_id"])

        self.request_json(
            "POST",
            f"/api/ocr/jobs/{job['ocr_job_id']}/result",
            payload={
                "raw_json": {"mock": True},
                "raw_text": "recognized formula text",
                "model_name": "test-model",
                "duration_ms": 20,
                "confidence": 0.9,
            },
            headers=self.worker_headers(),
        )

        listed = self.request_json("GET", "/api/questions?status=recognized")
        self.assertEqual(listed["total"], 1)
        self.assertEqual(listed["items"][0]["question_id"], upload["question_id"])
        self.assertEqual(listed["items"][0]["raw_text"], "recognized formula text")
        self.assertEqual(listed["items"][0]["latest_ocr_job"]["status"], "succeeded")
        self.assertEqual(listed["items"][0]["first_asset"]["asset_id"], upload["asset_id"])

        detail = self.request_json("GET", f"/api/questions/{upload['question_id']}")["question"]
        self.assertEqual(detail["status"], "recognized")
        self.assertEqual(len(detail["assets"]), 1)
        self.assertEqual(len(detail["ocr_jobs"]), 1)

        updated = self.request_json(
            "PATCH",
            f"/api/questions/{upload['question_id']}",
            payload={
                "subject": "math",
                "title": "Derivative practice",
                "corrected_text": "corrected formula text",
                "question_type": "calculation",
                "difficulty": "medium",
                "status": "corrected",
            },
        )["question"]
        self.assertEqual(updated["subject"], "math")
        self.assertEqual(updated["title"], "Derivative practice")
        self.assertEqual(updated["corrected_text"], "corrected formula text")
        self.assertEqual(updated["status"], "corrected")

        searched = self.request_json("GET", "/api/questions?q=corrected&subject=math")
        self.assertEqual(searched["total"], 1)
        self.assertEqual(searched["items"][0]["question_id"], upload["question_id"])

        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request_json(
                "PATCH",
                f"/api/questions/{upload['question_id']}",
                payload={"status": "bad-status"},
            )
        self.assertEqual(error.exception.code, 400)

    def test_mock_worker_processes_one_pending_job(self) -> None:
        upload = self.upload_image("worker.png")

        env = self.env.copy()
        env["SERVER_URL"] = self.base_url
        env["WORKER_TOKEN"] = WORKER_TOKEN
        env["WORKER_NAME"] = "test-mock-worker"
        env["POLL_INTERVAL"] = "0.1"
        env["OCR_ENGINE"] = "mock"

        completed = subprocess.run(
            [sys.executable, str(WORKER_SCRIPT), "--once"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )

        job = self.request_json(
            "GET",
            f"/api/ocr/jobs/{upload['ocr_job_id']}",
            headers=self.worker_headers(),
        )["job"]
        self.assertEqual(job["status"], "succeeded")
        self.assertEqual(job["worker_name"], "test-mock-worker")
        self.assertEqual(job["model_name"], "mock-ocr-worker")
        self.assertEqual(job["raw_text"], "mock OCR text from worker")
        self.assertIn('"downloaded_bytes"', job["raw_json"])

    @unittest.skipIf(
        importlib.util.find_spec("paddleocr") is not None
        and importlib.util.find_spec("paddle") is not None,
        "PaddleOCR is installed; missing-dependency failure path is not active.",
    )
    def test_paddle_engine_missing_dependencies_fail_pending_job(self) -> None:
        upload = self.upload_image("paddle.png")

        env = self.env.copy()
        env["SERVER_URL"] = self.base_url
        env["WORKER_TOKEN"] = WORKER_TOKEN
        env["WORKER_NAME"] = "test-paddle-worker"
        env["POLL_INTERVAL"] = "0.1"
        env["OCR_ENGINE"] = "paddle"

        completed = subprocess.run(
            [sys.executable, str(WORKER_SCRIPT), "--once"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            1,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )

        job = self.request_json(
            "GET",
            f"/api/ocr/jobs/{upload['ocr_job_id']}",
            headers=self.worker_headers(),
        )["job"]
        self.assertEqual(job["status"], "failed")
        self.assertEqual(job["worker_name"], "test-paddle-worker")
        self.assertIn("OCR_ENGINE=paddle", job["error_message"])


if __name__ == "__main__":
    unittest.main()

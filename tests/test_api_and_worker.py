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
        self.assertIn('id="knowledgePointList"', html)
        self.assertIn('id="createKnowledgePointButton"', html)
        self.assertIn('id="mistakeTagsInput"', html)
        self.assertIn('id="scheduleReviewButton"', html)
        self.assertIn('id="dueReviewList"', html)
        self.assertIn('id="questionPreviousButton"', html)
        self.assertIn('id="questionNextButton"', html)
        self.assertIn('id="reviewHistoryPreviousButton"', html)
        self.assertIn('id="reviewHistoryNextButton"', html)
        self.assertIn('id="reviewHistoryTitle"', html)
        self.assertIn('class="skip-link"', html)
        self.assertIn('id="mainContent"', html)
        self.assertIn('id="exportJsonButton"', html)
        self.assertIn('id="exportMarkdownButton"', html)
        self.assertIn('id="archiveQuestionButton"', html)
        self.assertIn('id="restoreQuestionButton"', html)
        self.assertIn('id="libraryStatsTitle"', html)
        self.assertIn('id="libraryKnowledgeStats"', html)
        self.assertIn('id="reviewStats"', html)
        self.assertIn('id="statsMasteredRate"', html)

        fallback_html, _ = self.request_text("GET", "/app/questions/1")
        self.assertIn("WrongBook", fallback_html)

        css, css_content_type = self.request_text("GET", "/app/static/app.css")
        self.assertIn("text/css", css_content_type)
        self.assertIn(".app-shell", css)

        javascript, js_content_type = self.request_text("GET", "/app/static/app.js")
        self.assertIn("javascript", js_content_type)
        self.assertIn("/api/questions/upload", javascript)
        self.assertIn("/api/questions/stats", javascript)
        self.assertIn("/export?format=", javascript)
        self.assertIn("setupKeyboardShortcuts", javascript)
        self.assertIn("requestSubmit", javascript)
        self.assertIn("questionOffset", javascript)
        self.assertIn("historyOffset", javascript)
        self.assertIn("questionPages", javascript)
        self.assertIn("historyPages", javascript)
        self.assertIn("/api/knowledge-points", javascript)
        self.assertIn("/knowledge-points", javascript)
        self.assertIn("/api/mistake-tags", javascript)
        self.assertIn("/mistake-tags", javascript)
        self.assertIn("/api/reviews/history", javascript)
        self.assertIn('handleArchiveAction("archive")', javascript)
        self.assertIn('handleArchiveAction("restore")', javascript)
        self.assertIn("/api/reviews/due", javascript)
        self.assertIn("/api/reviews/stats", javascript)
        self.assertIn("/reviews", javascript)
        self.assertIn("/complete", javascript)
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

    def test_question_export_formats(self) -> None:
        upload = self.upload_image("export.png")
        question_id = upload["question_id"]
        self.request_json(
            "PATCH",
            f"/api/questions/{question_id}",
            payload={"title": "Derivative / Practice", "subject": "Math", "corrected_text": "f(x)=xe^x"},
        )

        json_request = urllib.request.Request(f"{self.base_url}/api/questions/{question_id}/export?format=json")
        with urllib.request.urlopen(json_request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
            self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertEqual(payload["format"], "wrongbook-question")
        self.assertEqual(payload["question"]["corrected_text"], "f(x)=xe^x")

        markdown, content_type = self.request_text(
            "GET",
            f"/api/questions/{question_id}/export?format=markdown",
        )
        self.assertIn("text/markdown", content_type)
        self.assertIn("# Derivative / Practice", markdown)
        self.assertIn("## 校正文", markdown)
        self.assertIn("f(x)=xe^x", markdown)

    def test_detailed_health_and_api_pagination(self) -> None:
        health = self.request_json("GET", "/health/details")
        self.assertEqual(health["status"], "ok")
        self.assertTrue(health["database"]["ok"])
        self.assertTrue(health["uploads"]["writable"])
        self.assertTrue(health["disk"]["ok"])
        self.assertGreater(health["disk"]["free_bytes"], 0)

        first = self.upload_image("page-one.png")
        second = self.upload_image("page-two.png")
        page = self.request_json("GET", "/api/questions?limit=1&offset=1")
        self.assertEqual(page["total"], 2)
        self.assertEqual(len(page["items"]), 1)
        self.assertEqual(page["offset"], 1)
        self.assertIn(page["items"][0]["question_id"], {first["question_id"], second["question_id"]})

    def test_archive_and_review_history_flow(self) -> None:
        upload = self.upload_image("archive-history.png")
        question_id = upload["question_id"]

        with self.assertRaises(urllib.error.HTTPError) as restore_error:
            self.request_json("POST", f"/api/questions/{question_id}/restore")
        self.assertEqual(restore_error.exception.code, 409)

        archived = self.request_json("POST", f"/api/questions/{question_id}/archive")["question"]
        self.assertEqual(archived["status"], "archived")
        archived_again = self.request_json("POST", f"/api/questions/{question_id}/archive")["question"]
        self.assertEqual(archived_again["status"], "archived")
        restored = self.request_json("POST", f"/api/questions/{question_id}/restore")["question"]
        self.assertEqual(restored["status"], "corrected")

        review = self.request_json(
            "POST",
            f"/api/questions/{question_id}/reviews",
            payload={"due_at": "2026-07-10T09:00:00Z"},
        )["review"]
        self.request_json(
            "POST",
            f"/api/reviews/{review['review_id']}/complete",
            payload={"result": "hard"},
        )
        history = self.request_json(
            "GET",
            f"/api/reviews/history?result=hard&question_id={question_id}",
        )
        self.assertEqual(history["total"], 1)
        self.assertEqual(history["items"][0]["result"], "hard")
        self.assertEqual(history["items"][0]["question"]["question_id"], question_id)
        empty = self.request_json("GET", "/api/reviews/history?result=easy")
        self.assertEqual(empty["total"], 0)

    def test_question_statistics(self) -> None:
        first = self.upload_image("library-one.png")
        second = self.upload_image("library-two.png")
        third = self.upload_image("library-three.png")
        self.request_json("PATCH", f"/api/questions/{first['question_id']}", payload={"subject": "Math", "status": "corrected"})
        self.request_json("PATCH", f"/api/questions/{second['question_id']}", payload={"subject": "Math"})
        point = self.request_json(
            "POST",
            "/api/knowledge-points",
            payload={"name": "Algebra", "subject": "Math"},
        )["knowledge_point"]
        self.request_json(
            "PUT",
            f"/api/questions/{first['question_id']}/knowledge-points",
            payload={"ids": [point["knowledge_point_id"]]},
        )
        self.request_json(
            "PUT",
            f"/api/questions/{second['question_id']}/knowledge-points",
            payload={"ids": [point["knowledge_point_id"]]},
        )

        stats = self.request_json("GET", "/api/questions/stats")
        self.assertEqual(stats["total_questions"], 3)
        self.assertEqual(stats["status_counts"]["corrected"], 1)
        self.assertEqual(stats["status_counts"]["draft"], 2)
        self.assertEqual(stats["subject_counts"][0], {"subject": "Math", "question_count": 2})
        self.assertEqual(stats["subject_counts"][1], {"subject": "Uncategorized", "question_count": 1})
        self.assertEqual(stats["top_knowledge_points"][0]["name"], "Algebra")
        self.assertEqual(stats["top_knowledge_points"][0]["question_count"], 2)

    def test_review_statistics(self) -> None:
        first = self.upload_image("stats-one.png")
        second = self.upload_image("stats-two.png")
        now = "2026-07-11T12:00:00Z"
        old_due = "2026-07-10T09:00:00Z"

        first_review = self.request_json(
            "POST",
            f"/api/questions/{first['question_id']}/reviews",
            payload={"due_at": old_due},
        )["review"]
        self.request_json(
            "POST",
            f"/api/reviews/{first_review['review_id']}/complete",
            payload={"result": "good"},
        )
        self.request_json(
            "POST",
            f"/api/questions/{second['question_id']}/reviews",
            payload={"due_at": old_due},
        )

        stats = self.request_json("GET", f"/api/reviews/stats?now={now}")
        self.assertEqual(stats["due_count"], 1)
        self.assertEqual(stats["completed_seven_days"], 1)
        self.assertEqual(stats["result_counts_seven_days"]["good"], 1)
        self.assertEqual(stats["result_counts_seven_days"]["again"], 0)
        self.assertEqual(stats["mastered_rate_seven_days"], 1.0)

    def test_knowledge_point_management_flow(self) -> None:
        upload = self.upload_image("knowledge.png")
        question_id = upload["question_id"]

        algebra = self.request_json(
            "POST",
            "/api/knowledge-points",
            payload={"name": " Algebra ", "subject": " Mathematics "},
        )["knowledge_point"]
        quadratic = self.request_json(
            "POST",
            "/api/knowledge-points",
            payload={
                "name": "Quadratic Functions",
                "subject": "Mathematics",
                "parent_id": algebra["knowledge_point_id"],
            },
        )["knowledge_point"]
        self.assertEqual(algebra["name"], "Algebra")
        self.assertEqual(algebra["subject"], "Mathematics")
        self.assertEqual(quadratic["parent_id"], algebra["knowledge_point_id"])

        listed = self.request_json(
            "GET",
            "/api/knowledge-points?subject=mathematics&q=quadratic",
        )
        self.assertEqual(listed["total"], 1)
        self.assertEqual(listed["items"][0]["knowledge_point_id"], quadratic["knowledge_point_id"])

        with self.assertRaises(urllib.error.HTTPError) as duplicate_error:
            self.request_json(
                "POST",
                "/api/knowledge-points",
                payload={"name": "algebra", "subject": "MATHEMATICS"},
            )
        self.assertEqual(duplicate_error.exception.code, 409)

        assigned = self.request_json(
            "PUT",
            f"/api/questions/{question_id}/knowledge-points",
            payload={
                "ids": [
                    quadratic["knowledge_point_id"],
                    algebra["knowledge_point_id"],
                    quadratic["knowledge_point_id"],
                ]
            },
        )["question"]
        self.assertEqual(
            [point["name"] for point in assigned["knowledge_points"]],
            ["Algebra", "Quadratic Functions"],
        )

        detail = self.request_json("GET", f"/api/questions/{question_id}")["question"]
        self.assertEqual(len(detail["knowledge_points"]), 2)

        with self.assertRaises(urllib.error.HTTPError) as missing_error:
            self.request_json(
                "PUT",
                f"/api/questions/{question_id}/knowledge-points",
                payload={"ids": [999999]},
            )
        self.assertEqual(missing_error.exception.code, 404)

    def test_mistake_tags_and_review_schedule_flow(self) -> None:
        upload = self.upload_image("review.png")
        question_id = upload["question_id"]

        tagged = self.request_json(
            "PUT",
            f"/api/questions/{question_id}/mistake-tags",
            payload={"names": ["calculation", "concept", "Calculation"]},
        )["question"]
        self.assertEqual(
            [tag["name"] for tag in tagged["mistake_tags"]],
            ["calculation", "concept"],
        )

        tags = self.request_json("GET", "/api/mistake-tags?q=calc")
        self.assertEqual(tags["total"], 1)
        self.assertEqual(tags["items"][0]["name"], "calculation")

        review = self.request_json(
            "POST",
            f"/api/questions/{question_id}/reviews",
            payload={"due_at": "2026-01-01T00:00:00Z"},
        )["review"]
        self.assertEqual(review["question_id"], question_id)
        self.assertIsNone(review["reviewed_at"])

        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request_json(
                "POST",
                f"/api/questions/{question_id}/reviews",
                payload={"due_at": "2026-01-02T00:00:00Z"},
            )
        self.assertEqual(error.exception.code, 409)

        due = self.request_json("GET", "/api/reviews/due?before=2026-01-03T00:00:00Z")
        self.assertEqual(due["total"], 1)
        self.assertEqual(due["items"][0]["review_id"], review["review_id"])
        self.assertEqual(due["items"][0]["question"]["question_id"], question_id)

        completed = self.request_json(
            "POST",
            f"/api/reviews/{review['review_id']}/complete",
            payload={
                "result": "good",
                "next_due_at": "2030-01-01T00:00:00Z",
            },
        )
        self.assertEqual(completed["review"]["result"], "good")
        self.assertIsNotNone(completed["review"]["reviewed_at"])
        self.assertEqual(completed["next_review"]["question_id"], question_id)

        due_after_completion = self.request_json(
            "GET",
            "/api/reviews/due?before=2026-01-03T00:00:00Z",
        )
        self.assertEqual(due_after_completion["total"], 0)

        detail = self.request_json("GET", f"/api/questions/{question_id}")["question"]
        self.assertEqual(len(detail["reviews"]), 2)
        self.assertEqual(detail["next_review"]["review_id"], completed["next_review"]["review_id"])

        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request_json(
                "POST",
                f"/api/reviews/{completed['next_review']['review_id']}/complete",
                payload={"result": "invalid"},
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

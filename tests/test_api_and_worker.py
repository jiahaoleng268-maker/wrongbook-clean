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

    def upload_formula_crop(self, question_id: int, filename: str = "formula.png") -> dict:
        body, content_type = _multipart_body("file", filename, "image/png", TEST_IMAGE_BYTES)
        request = urllib.request.Request(
            f"{self.base_url}/api/questions/{question_id}/formula-ocr",
            data=body,
            headers={"Content-Type": content_type},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def test_formula_crop_job_preserves_question_text(self) -> None:
        upload = self.upload_image("source.png")
        question_id = upload["question_id"]
        self.request_json(
            "PATCH",
            f"/api/questions/{question_id}",
            payload={"corrected_text": "人工校正文"},
        )

        formula = self.upload_formula_crop(question_id)
        self.assertEqual(formula["asset"]["asset_type"], "formula_crop")
        self.assertEqual(formula["job"]["engine_name"], "formula")

        with self.assertRaises(urllib.error.HTTPError) as duplicate_error:
            self.upload_formula_crop(question_id, "duplicate.png")
        self.assertEqual(duplicate_error.exception.code, 409)

        self.request_json(
            "POST",
            f"/api/ocr/jobs/{formula['job']['ocr_job_id']}/result",
            payload={"raw_text": r"\frac{1}{x}", "raw_json": {"engine": "formula"}},
            headers=self.worker_headers(),
        )
        detail = self.request_json("GET", f"/api/questions/{question_id}")["question"]
        self.assertEqual(detail["corrected_text"], "人工校正文")
        self.assertNotEqual(detail["raw_text"], r"\frac{1}{x}")
        formula_jobs = [job for job in detail["ocr_jobs"] if job["engine_name"] == "formula"]
        self.assertEqual(formula_jobs[-1]["raw_text"], r"\frac{1}{x}")
    def test_question_asset_management(self) -> None:
        upload = self.upload_image("asset-source.png")
        question_id = upload["question_id"]
        body, content_type = _multipart_body("file", "answer.png", "image/png", TEST_IMAGE_BYTES)
        boundary = content_type.split("boundary=", 1)[1]
        body = body.replace(
            f"--{boundary}\r\n".encode("utf-8"),
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"asset_type\"\r\n\r\nanswer_image\r\n--{boundary}\r\n".encode("utf-8"),
            1,
        )
        request = urllib.request.Request(f"{self.base_url}/api/questions/{question_id}/assets", data=body, headers={"Content-Type": content_type}, method="POST")
        with urllib.request.urlopen(request, timeout=10) as response:
            asset = json.loads(response.read().decode("utf-8"))["asset"]
        self.assertEqual(asset["asset_type"], "answer_image")
        updated = self.request_json("PATCH", f"/api/assets/{asset['asset_id']}", payload={"asset_type": "solution_image"})["asset"]
        self.assertEqual(updated["asset_type"], "solution_image")
        self.request_json("DELETE", f"/api/assets/{asset['asset_id']}")
        detail = self.request_json("GET", f"/api/questions/{question_id}")["question"]
        self.assertNotIn(asset["asset_id"], [item["asset_id"] for item in detail["assets"]])

    def test_smart_filters_and_source_maintenance(self) -> None:
        source = self.request_json("POST", "/api/sources", payload={"name": "待重命名资料"})["source"]
        chapter = self.request_json("POST", "/api/chapters", payload={"source_id": source["source_id"], "name": "旧章节"})["chapter"]
        renamed_source = self.request_json("PATCH", f"/api/sources/{source['source_id']}", payload={"name": "新资料"})["source"]
        renamed_chapter = self.request_json("PATCH", f"/api/chapters/{chapter['chapter_id']}", payload={"name": "新章节"})["chapter"]
        self.assertEqual(renamed_source["name"], "新资料")
        self.assertEqual(renamed_chapter["name"], "新章节")
        upload = self.upload_image("smart-filter.png")
        unclassified = self.request_json("GET", "/api/questions?smart_filter=unclassified")
        missing_answer = self.request_json("GET", "/api/questions?smart_filter=missing_answer")
        self.assertIn(upload["question_id"], [item["question_id"] for item in unclassified["items"]])
        self.assertIn(upload["question_id"], [item["question_id"] for item in missing_answer["items"]])
        self.request_json("DELETE", f"/api/chapters/{chapter['chapter_id']}")
        self.request_json("DELETE", f"/api/sources/{source['source_id']}")

    def test_sorting_and_bulk_metadata_append(self) -> None:
        first = self.upload_image("sort-a.png")
        second = self.upload_image("sort-b.png")
        self.request_json("PATCH", f"/api/questions/{first['question_id']}", payload={"title": "B title"})
        self.request_json("PATCH", f"/api/questions/{second['question_id']}", payload={"title": "A title"})
        point = self.request_json("POST", "/api/knowledge-points", payload={"name": "矩阵秩", "subject": "线性代数"})["knowledge_point"]
        result = self.request_json("POST", "/api/questions/bulk-update", payload={"question_ids": [first["question_id"], second["question_id"]], "knowledge_point_ids": [point["knowledge_point_id"]], "mistake_tag_names": ["计算错误"]})
        self.assertEqual(result["updated_count"], 2)
        sorted_items = self.request_json("GET", "/api/questions?sort_by=title&sort_order=asc")["items"]
        selected = [item for item in sorted_items if item["question_id"] in {first["question_id"], second["question_id"]}]
        self.assertEqual([item["title"] for item in selected], ["A title", "B title"])
        detail = self.request_json("GET", f"/api/questions/{first['question_id']}")["question"]
        self.assertIn("矩阵秩", [item["name"] for item in detail["knowledge_points"]])
        self.assertIn("计算错误", [item["name"] for item in detail["mistake_tags"]])

    def test_source_filters_manual_assignment_and_bulk_update(self) -> None:
        source = self.request_json("POST", "/api/sources", payload={"name": "线代讲义"})["source"]
        chapter = self.request_json("POST", "/api/chapters", payload={"source_id": source["source_id"], "name": "矩阵"})["chapter"]
        first = self.upload_image("bulk-one.png")
        second = self.upload_image("bulk-two.png")
        result = self.request_json(
            "POST",
            "/api/questions/bulk-update",
            payload={
                "question_ids": [first["question_id"], second["question_id"]],
                "source_id": source["source_id"],
                "chapter_id": chapter["chapter_id"],
                "status": "corrected",
            },
        )
        self.assertEqual(result["updated_count"], 2)
        source_filtered = self.request_json("GET", f"/api/questions?source_id={source['source_id']}")
        chapter_filtered = self.request_json("GET", f"/api/questions?chapter_id={chapter['chapter_id']}")
        self.assertEqual(source_filtered["total"], 2)
        self.assertEqual(chapter_filtered["total"], 2)
        self.assertTrue(all(item["status"] == "corrected" for item in chapter_filtered["items"]))

    def test_source_chapter_and_structured_question_fields(self) -> None:
        source = self.request_json(
            "POST",
            "/api/sources",
            payload={"name": "高数基础篇", "source_type": "教材", "subject": "高等数学"},
        )["source"]
        chapter = self.request_json(
            "POST",
            "/api/chapters",
            payload={"source_id": source["source_id"], "name": "函数极限"},
        )["chapter"]
        upload = self.upload_image("structured.png")
        question_id = upload["question_id"]
        updated = self.request_json(
            "PATCH",
            f"/api/questions/{question_id}",
            payload={
                "source_id": source["source_id"],
                "chapter_id": chapter["chapter_id"],
                "source_page": "18",
                "answer_text": "1",
                "solution_text": r"使用 $\\lim_{x\\to0}\\frac{\\sin x}{x}=1$",
                "personal_solution": "等价无穷小",
                "wrong_answer": "0",
                "mistake_analysis": "忘记重要极限",
                "key_steps": "识别基本极限",
                "notes": "再次检查定义域",
            },
        )["question"]
        self.assertEqual(updated["source_record"]["name"], "高数基础篇")
        self.assertEqual(updated["chapter"]["name"], "函数极限")
        self.assertEqual(updated["source_page"], "18")
        self.assertEqual(updated["answer_text"], "1")
        self.assertEqual(updated["mistake_analysis"], "忘记重要极限")
        sources = self.request_json("GET", "/api/sources")["items"]
        self.assertEqual(sources[0]["chapters"][0]["name"], "函数极限")

    def test_manual_paddle_import_without_ocr_job(self) -> None:
        boundary = f"----wrongbook-manual-{time.time_ns()}"
        parts = [
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"title\"\r\n\r\n极限例题\r\n",
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"subject\"\r\n\r\n高等数学\r\n",
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"content\"\r\n\r\n求极限 $\\lim_{{x\\to0}}\\frac{{\\sin x}}{{x}}$\r\n",
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"question.png\"\r\nContent-Type: image/png\r\n\r\n".encode("utf-8"),
            TEST_IMAGE_BYTES,
            f"\r\n--{boundary}--\r\n",
        ]
        body = b"".join(part.encode("utf-8") if isinstance(part, str) else part for part in parts)
        request = urllib.request.Request(
            f"{self.base_url}/api/questions/manual",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            created = json.loads(response.read().decode("utf-8"))["question"]
        self.assertEqual(created["title"], "极限例题")
        self.assertEqual(created["subject"], "高等数学")
        self.assertIn("\\lim", created["corrected_text"])
        self.assertEqual(len(created["assets"]), 1)
        self.assertEqual(created["ocr_jobs"], [])

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
        self.assertIn('id="cameraInput"', html)
        self.assertIn('id="paddleTextInput"', html)
        self.assertIn('class="desktop-sidebar"', html)
        self.assertIn('id="sourceTree"', html)
        self.assertIn('id="answerTextInput"', html)
        self.assertIn('id="latexPreviewContent"', html)
        self.assertIn('id="assetGallery"', html)
        self.assertIn('/app/static/vendor/katex/katex.min.js', html)
        self.assertIn('id="galleryInput"', html)
        self.assertIn('data-target-view="library"', html)
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
        self.assertIn('id="exportFilteredJsonButton"', html)
        self.assertIn('id="exportFilteredMarkdownButton"', html)
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
        self.assertIn(".top-bar .ghost-button", css)
        self.assertIn(".app-shell > *", css)

        service_worker, service_worker_content_type = self.request_text("GET", "/app/service-worker.js")
        self.assertIn("javascript", service_worker_content_type)
        self.assertIn('wrongbook-web-v12', service_worker)

        javascript, js_content_type = self.request_text("GET", "/app/static/app.js")
        self.assertIn("javascript", js_content_type)
        self.assertIn("/api/questions/manual", javascript)
        self.assertIn("/api/questions/stats", javascript)
        self.assertIn("/api/questions/export?", javascript)
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
        self.assertIn("switchView", javascript)
        self.assertNotIn("elements.fileLabel", javascript)
        self.assertIn("elements.selectedImageName.textContent", javascript)
        self.assertIn("galleryInput", javascript)

        manifest = self.request_json("GET", "/app/static/manifest.webmanifest")
        self.assertEqual(manifest["short_name"], "WrongBook")
        self.assertEqual(manifest["name"], "WrongBook \u9519\u9898\u6574\u7406")
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

    def test_question_ocr_rerun_preserves_corrected_text(self) -> None:
        upload = self.upload_image("rerun.png")
        question_id = upload["question_id"]
        with self.assertRaises(urllib.error.HTTPError) as active_error:
            self.request_json("POST", f"/api/questions/{question_id}/ocr-jobs")
        self.assertEqual(active_error.exception.code, 409)

        job = self.request_json("GET", "/api/ocr/jobs/next", headers=self.worker_headers())["job"]
        self.request_json(
            "POST",
            f"/api/ocr/jobs/{job['ocr_job_id']}/result",
            payload={"raw_text": "first OCR"},
            headers=self.worker_headers(),
        )
        self.request_json(
            "PATCH",
            f"/api/questions/{question_id}",
            payload={"corrected_text": "manual correction", "status": "corrected"},
        )

        rerun = self.request_json("POST", f"/api/questions/{question_id}/ocr-jobs")
        self.assertEqual(rerun["job"]["status"], "pending")
        self.assertNotEqual(rerun["job"]["ocr_job_id"], upload["ocr_job_id"])
        self.assertEqual(rerun["question"]["corrected_text"], "manual correction")
        self.assertEqual(len(rerun["question"]["ocr_jobs"]), 2)

        rerun_job = self.request_json("GET", "/api/ocr/jobs/next", headers=self.worker_headers())["job"]
        self.request_json(
            "POST",
            f"/api/ocr/jobs/{rerun_job['ocr_job_id']}/result",
            payload={"raw_text": "second OCR"},
            headers=self.worker_headers(),
        )
        detail = self.request_json("GET", f"/api/questions/{question_id}")["question"]
        self.assertEqual(detail["raw_text"], "second OCR")
        self.assertEqual(detail["corrected_text"], "manual correction")
        self.assertEqual(detail["status"], "corrected")

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

    def test_filtered_question_collection_exports(self) -> None:
        first = self.upload_image("collection-one.png")
        second = self.upload_image("collection-two.png")
        self.request_json("PATCH", f"/api/questions/{first['question_id']}", payload={"title": "Algebra One", "subject": "Math", "status": "corrected"})
        self.request_json("PATCH", f"/api/questions/{second['question_id']}", payload={"title": "Geometry Two", "subject": "Math", "status": "draft"})

        request = urllib.request.Request(f"{self.base_url}/api/questions/export?format=json&status=corrected&q=Algebra")
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        self.assertEqual(payload["format"], "wrongbook-question-collection")
        self.assertEqual(payload["total_matching"], 1)
        self.assertEqual(payload["exported_count"], 1)
        self.assertEqual(payload["questions"][0]["title"], "Algebra One")

        markdown, content_type = self.request_text("GET", "/api/questions/export?format=markdown&status=draft")
        self.assertIn("text/markdown", content_type)
        self.assertIn("Geometry Two", markdown)
        self.assertNotIn("Algebra One", markdown)

    def test_question_json_import_creates_new_questions_and_reuses_metadata(self) -> None:
        payload = {
            "format": "wrongbook-question-collection",
            "version": 1,
            "questions": [
                {
                    "id": 999,
                    "title": "Imported Algebra",
                    "subject": "Math",
                    "raw_text": "x + 1 = 2",
                    "corrected_text": "x = 1",
                    "question_type": "calculation",
                    "difficulty": "easy",
                    "source": "legacy export",
                    "status": "corrected",
                    "knowledge_points": [{"id": 10, "name": "Linear equations", "subject": "Math"}],
                    "mistake_tags": [{"id": 20, "name": "Sign error"}],
                    "assets": [{"file_path": "must-not-import.png"}],
                    "ocr_jobs": [{"status": "succeeded"}],
                    "reviews": [{"result": "good"}],
                },
                {
                    "title": "Imported Geometry",
                    "subject": "Math",
                    "status": "draft",
                    "knowledge_points": [{"name": "Linear equations", "subject": "Math"}],
                    "mistake_tags": ["Sign error"],
                },
            ],
        }
        body, content_type = _multipart_body("file", "wrongbook.json", "application/json", json.dumps(payload).encode("utf-8"))
        request = urllib.request.Request(
            f"{self.base_url}/api/questions/import",
            data=body,
            headers={"Content-Type": content_type},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            imported = json.loads(response.read().decode("utf-8"))
        self.assertEqual(imported["imported_count"], 2)
        self.assertNotIn(999, imported["question_ids"])
        first = self.request_json("GET", f"/api/questions/{imported['question_ids'][0]}")["question"]
        second = self.request_json("GET", f"/api/questions/{imported['question_ids'][1]}")["question"]
        self.assertEqual(first["title"], "Imported Algebra")
        self.assertEqual(first["assets"], [])
        self.assertEqual(first["ocr_jobs"], [])
        self.assertEqual(first["reviews"], [])
        self.assertEqual(first["knowledge_points"][0]["knowledge_point_id"], second["knowledge_points"][0]["knowledge_point_id"])
        self.assertEqual(first["mistake_tags"][0]["mistake_tag_id"], second["mistake_tags"][0]["mistake_tag_id"])

    def test_question_json_import_rejects_invalid_format_without_partial_write(self) -> None:
        payload = {
            "format": "wrongbook-question-collection",
            "version": 1,
            "questions": [{"title": "Valid first"}, {"title": "Invalid second", "status": "unsafe"}],
        }
        body, content_type = _multipart_body("file", "wrongbook.json", "application/json", json.dumps(payload).encode("utf-8"))
        request = urllib.request.Request(
            f"{self.base_url}/api/questions/import",
            data=body,
            headers={"Content-Type": content_type},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request, timeout=10)
        self.assertEqual(error.exception.code, 400)
        questions = self.request_json("GET", "/api/questions?q=Valid%20first")
        self.assertEqual(questions["total"], 0)

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

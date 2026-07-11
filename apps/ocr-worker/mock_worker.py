import argparse
import json
import os
import sys
import time
from typing import Optional
import urllib.error
import urllib.request

from engines import OCRResult, build_engine


DEFAULT_SERVER_URL = "http://127.0.0.1:8000"
DEFAULT_WORKER_TOKEN = "change-me"
DEFAULT_WORKER_NAME = "local-mock-worker"
DEFAULT_POLL_INTERVAL = 3.0
DEFAULT_OCR_ENGINE = "mock"


class WorkerRequestError(Exception):
    pass


class MockOCRWorker:
    def __init__(
        self,
        server_url: str,
        worker_token: str,
        worker_name: str,
        ocr_engine: str,
        poll_interval: float,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.worker_token = worker_token
        self.worker_name = worker_name
        self.engine = build_engine(ocr_engine)
        self.poll_interval = poll_interval

    @property
    def headers(self) -> dict:
        return {
            "X-Worker-Token": self.worker_token,
            "X-Worker-Name": self.worker_name,
        }

    def _url(self, path: str) -> str:
        return f"{self.server_url}{path}"

    def _request_json(
        self,
        method: str,
        path: str,
        payload: Optional[dict] = None,
    ) -> dict:
        data = None
        headers = dict(self.headers)

        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            self._url(path),
            data=data,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise WorkerRequestError(f"{method} {path} failed with {exc.code}: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise WorkerRequestError(f"{method} {path} failed: {exc.reason}") from exc

        if not body:
            return {}

        return json.loads(body)

    def _download_asset(self, asset_id: int) -> bytes:
        request = urllib.request.Request(
            self._url(f"/api/assets/{asset_id}/file"),
            headers=self.headers,
            method="GET",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise WorkerRequestError(
                f"GET /api/assets/{asset_id}/file failed with {exc.code}: {error_body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise WorkerRequestError(f"GET /api/assets/{asset_id}/file failed: {exc.reason}") from exc

    def claim_next_job(self) -> Optional[dict]:
        payload = self._request_json("GET", "/api/ocr/jobs/next")
        return payload.get("job")

    def submit_result(
        self,
        ocr_job_id: int,
        asset_id: int,
        file_path: Optional[str],
        image_bytes: bytes,
        ocr_result: OCRResult,
        duration_ms: int,
    ) -> dict:
        raw_json = {
            "engine": self.engine.name,
            "asset_id": asset_id,
            "file_path": file_path,
            "downloaded_bytes": len(image_bytes),
            "worker_name": self.worker_name,
        }
        if isinstance(ocr_result.raw_json, dict):
            raw_json.update(ocr_result.raw_json)
        elif ocr_result.raw_json is not None:
            raw_json["result"] = ocr_result.raw_json

        payload = {
            "raw_json": raw_json,
            "raw_text": ocr_result.raw_text,
            "model_name": ocr_result.model_name,
            "duration_ms": duration_ms,
            "confidence": ocr_result.confidence,
        }
        return self._request_json("POST", f"/api/ocr/jobs/{ocr_job_id}/result", payload)

    def submit_failure(self, ocr_job_id: int, error_message: str) -> None:
        payload = {"error_message": error_message[:4000]}
        self._request_json("POST", f"/api/ocr/jobs/{ocr_job_id}/fail", payload)

    def process_job(self, job: dict) -> None:
        ocr_job_id = job["ocr_job_id"]
        asset_id = job["asset_id"]
        file_path = job.get("file_path")
        started = time.monotonic()

        try:
            if asset_id is None:
                raise WorkerRequestError("OCR job has no asset_id.")

            image_bytes = self._download_asset(asset_id)
            ocr_result = self.engine.recognize(image_bytes=image_bytes, job=job)
            duration_ms = int((time.monotonic() - started) * 1000)
            result = self.submit_result(
                ocr_job_id=ocr_job_id,
                asset_id=asset_id,
                file_path=file_path,
                image_bytes=image_bytes,
                ocr_result=ocr_result,
                duration_ms=duration_ms,
            )
            status = result.get("job", {}).get("status")
            print(f"Job {ocr_job_id} submitted with status={status}")
        except Exception as exc:
            print(f"Job {ocr_job_id} failed: {exc}", file=sys.stderr)
            try:
                self.submit_failure(ocr_job_id, str(exc))
            except Exception as fail_exc:
                print(f"Failed to submit failure for job {ocr_job_id}: {fail_exc}", file=sys.stderr)
            raise

    def run(self, once: bool = False) -> int:
        while True:
            try:
                job = self.claim_next_job()
            except Exception as exc:
                print(f"Failed to poll OCR job: {exc}", file=sys.stderr)
                if once:
                    return 1
                time.sleep(self.poll_interval)
                continue

            if job is None:
                print("No pending OCR job.")
                if once:
                    return 0
                time.sleep(self.poll_interval)
                continue

            print(
                "Claimed job "
                f"{job['ocr_job_id']} for asset {job.get('asset_id')} "
                f"from {job.get('file_path')}"
            )

            try:
                self.process_job(job)
            except Exception:
                if once:
                    return 1

            if once:
                return 0


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default

    try:
        return float(value)
    except ValueError:
        return default


def build_worker() -> MockOCRWorker:
    return MockOCRWorker(
        server_url=os.getenv("SERVER_URL", DEFAULT_SERVER_URL),
        worker_token=os.getenv("WORKER_TOKEN", DEFAULT_WORKER_TOKEN),
        worker_name=os.getenv("WORKER_NAME", DEFAULT_WORKER_NAME),
        ocr_engine=os.getenv("OCR_ENGINE", DEFAULT_OCR_ENGINE),
        poll_interval=_env_float("POLL_INTERVAL", DEFAULT_POLL_INTERVAL),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the WrongBook OCR Worker.")
    parser.add_argument("--once", action="store_true", help="Poll once and exit.")
    args = parser.parse_args()

    return build_worker().run(once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())

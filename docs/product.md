# Product Notes

WrongBook is a personal wrong-question organization tool. It is designed for collecting questions from photos, extracting text through OCR, correcting the extracted content, classifying questions, and reviewing them later.

## Product Goal

The goal is to make wrong-question collection fast enough that it becomes part of normal study flow:

1. Take a photo on a phone.
2. Upload it through a browser or PWA.
3. Let OCR extract the question text.
4. Manually correct OCR mistakes.
5. Classify the question by subject, topic, source, and mistake type.
6. Review the question later.

The product should prioritize reliability, simple workflows, and easy local operation over heavy infrastructure.

## Core Flow

The intended workflow is:

```text
photo -> upload -> OCR -> correction -> classification -> review
```

The phone is used for capture and quick upload. The server stores the image, metadata, OCR job, and corrected result. The Windows laptop runs PaddleOCR Worker and sends OCR results back to the server.

## MVP Scope

The first version should include:

- FastAPI backend
- SQLite database
- local image storage
- image upload API
- OCR job table and API
- polling OCR Worker protocol
- Windows OCR Worker mock mode
- later PaddleOCR mode on the Windows laptop
- simple Vue 3 + Vite tool interface
- basic question correction and classification
- basic review list
- simple backup workflow

The first version should not require heavy services or distributed infrastructure.

## Not In Scope Yet

These are intentionally not part of the first version:

- WeChat Mini Program
- complex multi-user account system
- paid subscription or public SaaS features
- model fine-tuning
- server-side OCR
- server-side large language models
- Redis
- Celery
- PostgreSQL
- MinIO
- Elasticsearch
- Kubernetes
- complex recommendation algorithms
- mobile native apps

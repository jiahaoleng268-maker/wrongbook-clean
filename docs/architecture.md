# Architecture

WrongBook uses a lightweight split architecture:

- phone browser or PWA for capture and upload
- low-resource server for Web, API, SQLite, image storage, OCR job queue, and backups
- Windows laptop for PaddleOCR Worker

The design keeps expensive OCR work away from the server.

## Components

```text
Phone browser/PWA
  -> Server Web/API
  -> SQLite and image storage
  -> OCR job queue
  <- Windows PaddleOCR Worker polls jobs and submits results
```

## Server Responsibilities

The server is responsible for:

- serving the API
- later serving the web frontend
- storing uploaded images
- storing metadata in SQLite
- creating OCR jobs
- exposing polling endpoints for the OCR Worker
- receiving OCR results
- storing corrected question text
- supporting classification and review workflows
- creating backups

The server should stay small and predictable. The target server is only 2 CPU cores, 2 GB RAM, and 50 GB disk.

## Windows Laptop Responsibilities

The Windows laptop is responsible for:

- running the OCR Worker
- downloading images from the server
- loading PaddleOCR models from the local model directory
- running OCR
- writing local logs and temporary files
- submitting OCR results back to the server

Planned local paths:

```text
D:\Code\WB\wrongbook-models\paddleocr
D:\Code\WB\wrongbook-runtime
D:\Code\WB\wrongbook-runtime\downloads
D:\Code\WB\wrongbook-runtime\logs
D:\Code\WB\wrongbook-runtime\temp
D:\Code\WB\wrongbook-backups
```

## Phone Browser/PWA Responsibilities

The phone browser or PWA is responsible for:

- taking or selecting photos
- uploading question images
- showing upload status
- later supporting correction, classification, and review workflows

The phone should not need special native app installation for the first version.

## Why The Server Does Not Run OCR

The server should not run OCR because:

- OCR is CPU and memory intensive.
- PaddleOCR model files are large.
- The server has limited CPU, memory, and disk.
- OCR spikes could slow down normal API and web usage.
- The Windows laptop has a more suitable local runtime for OCR work.

This split keeps the server stable while still allowing high-quality OCR.

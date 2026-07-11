# Local PaddleOCR Setup

This document records the Windows laptop OCR setup. PaddleOCR must run only on the local laptop Worker, not on the 2c2g server.

## Verified Local Environment

```text
GPU: NVIDIA GeForce RTX 5070 Laptop
Driver: 591.86
Driver CUDA capability shown by nvidia-smi: 13.1
Python: 3.12.13 in D:\Code\WB\wrongbook\.venv
PaddlePaddle: 3.3.0 GPU, CUDA 13.0 wheel
PaddleOCR: 3.7.0
```

## Installed Packages

The local Windows `.venv` was installed with:

```powershell
cd D:\Code\WB\wrongbook
.\.venv\Scripts\Activate.ps1
python -m pip install paddlepaddle-gpu==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu130/
python -m pip install paddleocr
```

Do not add `.venv` to Git.

## Model Location

PaddleOCR first downloaded official models to the user cache. The verified model directories were copied to:

```text
D:\Code\WB\wrongbook-models\paddleocr\PP-OCRv6_medium_det
D:\Code\WB\wrongbook-models\paddleocr\PP-OCRv6_medium_rec
```

Do not add model files to Git.

## Worker Configuration

Use mock mode by default:

```env
OCR_ENGINE=mock
```

Use PaddleOCR mode only on the Windows laptop:

```env
OCR_ENGINE=paddle
PADDLEOCR_DEVICE=gpu
PADDLEOCR_LANG=ch
MODEL_ROOT=D:\Code\WB\wrongbook-models\paddleocr
```

## Verification

PaddlePaddle GPU verification passed after adding the pip-installed NVIDIA DLL directories to `PATH`. The Worker now does this automatically for the common pip wheel layout:

```text
.venv\Lib\site-packages\nvidia\cu13\bin\x86_64
.venv\Lib\site-packages\nvidia\cudnn\bin
```

Manual OCR verification on `D:\Code\WB\testImage\test1.png` returned recognized text and a confidence score using the local model directories.
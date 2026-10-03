from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile

from . import config, ocr
from .embeddings import get_embedder
from .evaluator import evaluate
from .schemas import EvaluateRequest, EvaluateResponse, OcrResponse

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="InkGrade AI Service", version="1.0.0",
              description="Handwriting OCR and semantic answer evaluation")

MAX_BYTES = 25 * 1024 * 1024


def check_key(x_api_key: str = Header(default="")):
    if config.API_KEY and x_api_key != config.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/health")
def health():
    return {"status": "ok", "ocr_engine": config.OCR_ENGINE, "embedding_backend": get_embedder().name}


@app.post("/ocr", response_model=OcrResponse, dependencies=[Depends(check_key)])
async def run_ocr(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File too large")
    try:
        return ocr.extract(data, file.filename or "", file.content_type or "")
    except ocr.OcrUnavailable as exc:
        raise HTTPException(503, str(exc))
    except Exception as exc:  # noqa: BLE001
        logging.exception("OCR failed")
        raise HTTPException(422, f"Could not process file: {exc}")


@app.post("/evaluate", response_model=EvaluateResponse, dependencies=[Depends(check_key)])
def run_evaluate(req: EvaluateRequest):
    if not req.questions:
        raise HTTPException(400, "At least one question is required")
    return evaluate(req)

from __future__ import annotations

import io
import logging
import shutil
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image

from . import config
from .schemas import OcrResponse, OcrWord

log = logging.getLogger("inkgrade.ocr")


class OcrUnavailable(RuntimeError):
    pass


def preprocess(img: np.ndarray) -> np.ndarray:
    """Grayscale -> denoise -> adaptive threshold -> deskew."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    h, w = gray.shape[:2]
    if max(h, w) < 1600:
        scale = 1600 / max(h, w)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.fastNlMeansDenoising(gray, None, 15, 7, 21)
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 15)
    return _deskew(bw)


def _deskew(bw: np.ndarray) -> np.ndarray:
    coords = np.column_stack(np.where(bw < 128))
    if len(coords) < 200:
        return bw
    angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    if abs(angle) < 0.3 or abs(angle) > 15:
        return bw
    h, w = bw.shape
    m = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(bw, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE, borderValue=255)


def extract(data: bytes, filename: str, content_type: str = "") -> OcrResponse:
    name = (filename or "").lower()
    if name.endswith(".txt") or content_type.startswith("text/"):
        return OcrResponse(text=data.decode("utf-8", errors="replace"), confidence=1.0, pages=1, engine="plaintext")
    if name.endswith(".pdf") or data[:4] == b"%PDF":
        return _from_pdf(data)
    return _from_images([_decode_image(data)])


def _decode_image(data: bytes) -> np.ndarray:
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        pil = Image.open(io.BytesIO(data)).convert("RGB")
        img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    return img


def _from_pdf(data: bytes) -> OcrResponse:
    import fitz  # PyMuPDF

    doc = fitz.open(stream=data, filetype="pdf")
    pages = min(len(doc), config.MAX_PDF_PAGES)
    texts = [doc[i].get_text() for i in range(pages)]
    if sum(len(t.strip()) for t in texts) > 50:  # digital PDF with a text layer
        return OcrResponse(text="\n".join(texts), confidence=1.0, pages=pages, engine="pdf-text")
    images = []
    for i in range(pages):
        pix = doc[i].get_pixmap(dpi=200)
        arr = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)
        images.append(cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR if pix.n == 4 else cv2.COLOR_RGB2BGR))
    return _from_images(images)


def _from_images(images: List[np.ndarray]) -> OcrResponse:
    if config.OCR_ENGINE == "trocr":
        return _trocr(images)
    return _tesseract(images)


def _tesseract(images: List[np.ndarray]) -> OcrResponse:
    import pytesseract

    if not shutil.which("tesseract"):
        raise OcrUnavailable("Tesseract binary not installed in the AI service environment")
    texts, words, confs = [], [], []
    for page, img in enumerate(images, start=1):
        bw = preprocess(img)
        d = pytesseract.image_to_data(bw, config="--oem 1 --psm 6", output_type=pytesseract.Output.DICT)
        lines = {}
        for i, t in enumerate(d["text"]):
            t = t.strip()
            conf = float(d["conf"][i])
            if not t or conf < 0:
                continue
            key = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
            lines.setdefault(key, []).append(t)
            confs.append(conf)
            words.append(OcrWord(text=t, page=page, left=d["left"][i], top=d["top"][i], width=d["width"][i],
                                 height=d["height"][i], confidence=conf / 100))
        texts.append("\n".join(" ".join(v) for v in lines.values()))
    conf = (sum(confs) / len(confs) / 100) if confs else 0.0
    return OcrResponse(text="\n".join(texts), confidence=round(conf, 3), pages=len(images), engine="tesseract",
                       words=words)


_trocr_cache: Tuple = ()


def _trocr(images: List[np.ndarray]) -> OcrResponse:
    """Line-level handwriting recognition with TrOCR (requires requirements-ml.txt)."""
    global _trocr_cache
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    if not _trocr_cache:
        _trocr_cache = (TrOCRProcessor.from_pretrained(config.TROCR_MODEL),
                        VisionEncoderDecoderModel.from_pretrained(config.TROCR_MODEL))
    processor, model = _trocr_cache
    out_lines = []
    for img in images:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 15)
        profile = bw.sum(axis=1) / 255
        thresh = max(2, profile.max() * 0.05)
        in_line, start = False, 0
        for y, v in enumerate(profile):
            if v > thresh and not in_line:
                in_line, start = True, y
            elif v <= thresh and in_line:
                in_line = False
                if y - start >= 12:
                    out_lines.append(_trocr_line(processor, model, img[max(0, start - 4):y + 4]))
    text = "\n".join(l for l in out_lines if l)
    return OcrResponse(text=text, confidence=0.75, pages=len(images), engine="trocr")


def _trocr_line(processor, model, crop: np.ndarray) -> str:
    pil = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
    pixel = processor(images=pil, return_tensors="pt").pixel_values
    ids = model.generate(pixel, max_new_tokens=96)
    return processor.batch_decode(ids, skip_special_tokens=True)[0].strip()

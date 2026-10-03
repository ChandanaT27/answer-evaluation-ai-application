import os

EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "auto")  # auto | sbert | hash
SBERT_MODEL = os.getenv("SBERT_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
OCR_ENGINE = os.getenv("OCR_ENGINE", "tesseract")  # tesseract | trocr
TROCR_MODEL = os.getenv("TROCR_MODEL", "microsoft/trocr-base-handwritten")
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "40"))
API_KEY = os.getenv("AI_API_KEY", "")  # shared secret with backend; empty disables the check

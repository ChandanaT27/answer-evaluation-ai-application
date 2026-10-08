import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["STORAGE_ROOT"] = tempfile.mkdtemp(prefix="inkgrade-test-")
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-123"
os.environ["AI_API_KEY"] = ""
for k in ("DB_URL", "SEED_DEMO"):
    os.environ.pop(k, None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import ai_client  # noqa: E402
from app.main import app  # noqa: E402


def _fake_ocr(path, filename):
    return {"text": "Q1. answer one\nQ2. answer two", "confidence": 0.9, "pages": 1, "engine": "mock"}


def _fake_evaluate(req):
    results = []
    for q in req["questions"]:
        results.append({
            "question_id": q["id"], "question_number": q["number"], "answer_text": f"answer {q['number']} proces",
            "answer_found": True, "max_marks": q["max_marks"], "suggested_marks": q["max_marks"] / 2,
            "similarity": 0.5, "concept_coverage": 0.5, "matched_concepts": ["alpha"], "missing_concepts": ["beta"],
            "mistakes": [
                {"type": "SPELLING", "description": "Possible spelling error: 'proces'", "snippet": "proces",
                 "start_offset": 9, "end_offset": 15, "suggestion": "process"},
                {"type": "MISSING_CONCEPT", "description": "Missing concept: beta", "snippet": None,
                 "start_offset": None, "end_offset": None, "suggestion": None}],
            "feedback": "Partially correct.", "confidence": 0.8})
    return {"results": results, "embedding_backend": "mock"}


@pytest.fixture(scope="session")
def client():
    ai_client.ocr = _fake_ocr
    ai_client.evaluate = _fake_evaluate
    with TestClient(app) as c:
        yield c

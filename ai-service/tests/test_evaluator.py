from fastapi.testclient import TestClient

from app.main import app
from app.segmentation import split_answers

client = TestClient(app)

Q = [
    {"id": 1, "number": 1, "text": "What is photosynthesis?", "max_marks": 5,
     "model_answer": "Photosynthesis is the process by which plants convert sunlight, water and carbon dioxide into glucose and oxygen using chlorophyll.",
     "concepts": [{"name": "sunlight", "keywords": ["light energy"], "weight": 1},
                  {"name": "chlorophyll", "keywords": ["green pigment"], "weight": 1},
                  {"name": "glucose", "keywords": ["sugar"], "weight": 1},
                  {"name": "oxygen release", "keywords": ["releases oxygen"], "weight": 1}]},
    {"id": 2, "number": 2, "text": "Define gravity.", "max_marks": 2,
     "model_answer": "Gravity is the force of attraction between masses.",
     "concepts": [{"name": "force of attraction", "keywords": ["pulls"], "weight": 1}]},
]

TEXT = """Q1. Photosynthesis is the proces where plants use light energy from the sun, water and carbon dioxide
to make sugar. The green pigment chlorophyll absorbs the light. Oxygen is released.
Q2. Gravity is a taste of fruit.
"""


def test_segmentation():
    seg = split_answers("1. foo\n2) bar\n3: baz", [1, 2, 3])
    assert seg == {1: "foo", 2: "bar", 3: "baz"}
    seg = split_answers("Ans 1 alpha\n1. list item\nAnswer 2: beta", [1, 2])
    assert seg[1].startswith("alpha") and seg[2] == "beta"


def test_evaluate_semantic_concepts_and_mistakes():
    r = client.post("/evaluate", json={"text": TEXT, "ocr_confidence": 0.9, "questions": Q})
    assert r.status_code == 200
    res = {x["question_number"]: x for x in r.json()["results"]}
    q1, q2 = res[1], res[2]
    assert set(q1["matched_concepts"]) >= {"sunlight", "chlorophyll", "glucose"}  # synonyms matched
    assert q1["suggested_marks"] >= 3.5
    assert any(m["type"] == "SPELLING" and m["snippet"] == "proces" for m in q1["mistakes"])
    assert q2["suggested_marks"] < q1["suggested_marks"]
    assert "force of attraction" in q2["missing_concepts"]
    assert 0 <= q1["confidence"] <= 1


def test_unanswered_question_gets_zero():
    r = client.post("/evaluate", json={"text": "Q1. Gravity.", "questions": Q})
    res = {x["question_number"]: x for x in r.json()["results"]}
    assert res[2]["answer_found"] is False and res[2]["suggested_marks"] == 0


def test_ocr_plaintext_and_validation():
    r = client.post("/ocr", files={"file": ("a.txt", b"Q1. hello", "text/plain")})
    assert r.status_code == 200 and "hello" in r.json()["text"]
    assert client.post("/evaluate", json={"text": "x", "questions": []}).status_code == 400

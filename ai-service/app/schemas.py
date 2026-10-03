from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class OcrWord(BaseModel):
    text: str
    page: int
    left: int
    top: int
    width: int
    height: int
    confidence: float


class OcrResponse(BaseModel):
    text: str
    confidence: float
    pages: int
    engine: str
    words: List[OcrWord] = []


class ConceptIn(BaseModel):
    name: str
    keywords: List[str] = []
    weight: float = Field(1.0, gt=0)


class QuestionIn(BaseModel):
    model_config = {"protected_namespaces": ()}

    id: int
    number: int
    text: str = ""
    max_marks: float = Field(..., gt=0)
    model_answer: str = ""
    concepts: List[ConceptIn] = []


class EvaluateRequest(BaseModel):
    text: str
    ocr_confidence: float = 1.0
    questions: List[QuestionIn]


class MistakeOut(BaseModel):
    type: str  # SPELLING | GRAMMAR | MISSING_CONCEPT | INCORRECT_CONTENT
    description: str
    snippet: Optional[str] = None
    start_offset: Optional[int] = None  # offsets into answer_text
    end_offset: Optional[int] = None
    suggestion: Optional[str] = None


class QuestionResult(BaseModel):
    question_id: int
    question_number: int
    answer_text: str
    answer_found: bool
    max_marks: float
    suggested_marks: float
    similarity: float
    concept_coverage: float
    matched_concepts: List[str]
    missing_concepts: List[str]
    mistakes: List[MistakeOut]
    feedback: str
    confidence: float


class EvaluateResponse(BaseModel):
    results: List[QuestionResult]
    embedding_backend: str

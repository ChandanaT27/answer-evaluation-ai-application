import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from sqlalchemy import select

from .. import ai_client, mapper
from ..db import SessionLocal
from ..models import (Blueprint, Evaluation, EvaluationHistory, Feedback, Mistake, MistakeType, Question,
                      QuestionEvaluation, QeMatchedConcept, QeMissingConcept, StudentAnswer, Submission,
                      SubmissionStatus, EvaluationStatus)
from ..storage import storage
from . import audit

log = logging.getLogger("inkgrade.runner")
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="evaluation")
_MISTAKE_TYPES = {m.value for m in MistakeType}


def submit(submission_id: int, user_id: Optional[int], username: Optional[str]):
    return _pool.submit(run, submission_id, user_id, username)


def _trim(s: Optional[str], n: int) -> Optional[str]:
    return s if s is None or len(s) <= n else s[:n]


def _prepare(submission_id: int):
    with SessionLocal() as db:
        s = db.get(Submission, submission_id)
        questions = []
        for q in db.scalars(select(Question).where(Question.exam_id == s.exam_id).order_by(Question.number)):
            b = db.scalar(select(Blueprint).where(Blueprint.question_id == q.id))
            concepts = [{"name": c.name, "keywords": mapper.split_keywords(c.keywords), "weight": c.weight}
                        for c in (b.concepts if b else [])]
            questions.append({"id": q.id, "number": q.number, "text": q.text, "max_marks": q.max_marks,
                              "model_answer": (b.model_answer if b and b.model_answer else ""),
                              "concepts": concepts})
        return s.file_path, s.original_file_name, s.ocr_text, s.ocr_confidence, questions


def run(submission_id: int, user_id: Optional[int], username: Optional[str]) -> None:
    try:
        file_path, file_name, text, conf, questions = _prepare(submission_id)
        conf = 1.0 if conf is None else conf
        if text is None:
            ocr = ai_client.ocr(storage.resolve(file_path), file_name)
            text = ocr.get("text") or ""
            conf = float(ocr.get("confidence") or 0.0)
            with SessionLocal() as db:
                s = db.get(Submission, submission_id)
                if s is not None:
                    s.ocr_text, s.ocr_confidence = text, conf
                    db.commit()
        if not text.strip():
            raise RuntimeError("No text could be recognised in the answer sheet")
        resp = ai_client.evaluate({"text": text, "ocr_confidence": conf, "questions": questions})
        with SessionLocal() as db:
            ev_id = _persist(db, submission_id, resp, user_id, username)
            audit.log_as(db, user_id, username, "EVALUATION_COMPLETED", "Evaluation", ev_id,
                         f"Submission {submission_id}")
            db.commit()
    except Exception as e:  # noqa: BLE001 - any failure marks the submission FAILED
        log.exception("Evaluation of submission %s failed", submission_id)
        msg = getattr(e, "message", None) or str(e) or type(e).__name__
        msg = msg[:900]
        with SessionLocal() as db:
            s = db.get(Submission, submission_id)
            if s is not None:
                s.status = SubmissionStatus.FAILED.value
                s.error_message = msg
            audit.log_as(db, user_id, username, "EVALUATION_FAILED", "Submission", submission_id, msg)
            db.commit()


def _persist(db, submission_id: int, resp: dict, user_id, username) -> int:
    sub = db.get(Submission, submission_id)
    old = db.scalar(select(Evaluation).where(Evaluation.submission_id == submission_id))
    if old is not None:
        db.delete(old)
        db.flush()
    by_id = {q.id: q for q in db.scalars(select(Question).where(Question.exam_id == sub.exam_id))}
    existing = {a.question_id: a for a in db.scalars(
        select(StudentAnswer).where(StudentAnswer.submission_id == submission_id))}

    ev = Evaluation(submission=sub, embedding_backend=resp.get("embedding_backend"),
                    status=EvaluationStatus.AI_COMPLETED.value)
    max_total = sum(q.max_marks for q in by_id.values())
    total = 0.0
    for r in resp.get("results") or []:
        q = by_id.get(r.get("question_id"))
        if q is None:
            continue
        sa = existing.get(q.id) or StudentAnswer(submission_id=submission_id, question=q)
        sa.answer_text = r.get("answer_text")
        sa.found = bool(r.get("answer_found"))
        db.add(sa)

        marks = max(0.0, min(q.max_marks, float(r.get("suggested_marks") or 0.0)))
        qe = QuestionEvaluation(
            question=q, question_number=q.number, answer_text=r.get("answer_text"),
            answer_found=bool(r.get("answer_found")), max_marks=q.max_marks, ai_marks=marks,
            confidence=max(0.0, min(1.0, float(r.get("confidence") or 0.0))),
            similarity=float(r.get("similarity") or 0.0), concept_coverage=float(r.get("concept_coverage") or 0.0))
        for c in dict.fromkeys(r.get("matched_concepts") or []):
            qe.matched_rows.append(QeMatchedConcept(concept=c[:200]))
        for c in dict.fromkeys(r.get("missing_concepts") or []):
            qe.missing_rows.append(QeMissingConcept(concept=c[:200]))
        for m in r.get("mistakes") or []:
            mtype = m.get("type")
            if mtype not in _MISTAKE_TYPES or mtype == MistakeType.MISSING_CONCEPT.value:
                continue  # missing concepts are stored separately
            qe.mistakes.append(Mistake(
                type=mtype, description=_trim(m.get("description") or "", 500), snippet=_trim(m.get("snippet"), 1000),
                start_offset=m.get("start_offset"), end_offset=m.get("end_offset"),
                suggestion=_trim(m.get("suggestion"), 300)))
        fb = r.get("feedback")
        if fb and fb.strip():
            qe.feedbacks.append(Feedback(source="AI", text=fb))
        ev.question_evaluations.append(qe)
        total += marks
    ev.max_total = max_total
    ev.ai_total = total
    ev.final_total = total
    db.add(ev)
    sub.status = SubmissionStatus.EVALUATED.value
    sub.error_message = None
    db.flush()
    db.add(EvaluationHistory(evaluation_id=ev.id, submission_id=submission_id, action="AI_EVALUATED",
                             new_marks=total, note=f"Embedding backend: {resp.get('embedding_backend')}",
                             changed_by_id=user_id, changed_by_name=username))
    db.flush()
    return ev.id

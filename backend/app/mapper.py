from datetime import datetime, timezone
from math import floor
from typing import Any, Dict, List, Optional

from .models import (Blueprint, Evaluation, Exam, Question, QuestionEvaluation, Student, Subject, Submission,
                     Teacher, User)

Json = Dict[str, Any]


def iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def round2(v: float) -> float:
    return floor(v * 100 + 0.5) / 100.0


def pct(value: float, maximum: float) -> float:
    return floor(value / maximum * 10000.0 + 0.5) / 100.0 if maximum > 0 else 0.0


def split_keywords(s: Optional[str]) -> List[str]:
    if not s or not s.strip():
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def user(u: User, s: Optional[Student], t: Optional[Teacher]) -> Json:
    return {
        "id": u.id, "username": u.username, "email": u.email, "fullName": u.full_name, "role": u.role.name,
        "enabled": u.enabled, "rollNumber": s.roll_number if s else None, "className": s.class_name if s else None,
        "employeeId": t.employee_id if t else None, "department": t.department if t else None,
        "permissions": sorted(u.role.permissions), "createdAt": iso(u.created_at), "lastLoginAt": iso(u.last_login_at)}


def student(s: Student) -> Json:
    return {"id": s.id, "userId": s.user.id, "fullName": s.user.full_name, "rollNumber": s.roll_number,
            "className": s.class_name}


def subject(s: Subject, exam_count: int) -> Json:
    return {"id": s.id, "name": s.name, "code": s.code, "description": s.description, "active": s.active,
            "examCount": exam_count}


def exam(e: Exam, total_marks: float, question_count: int) -> Json:
    return {"id": e.id, "title": e.title, "subjectId": e.subject.id, "subjectName": e.subject.name,
            "teacherId": e.teacher.id, "teacherName": e.teacher.user.full_name,
            "examDate": e.exam_date.isoformat() if e.exam_date else None, "instructions": e.instructions,
            "hasQuestionPaper": e.question_paper_path is not None, "questionPaperName": e.question_paper_name,
            "totalMarks": total_marks, "questionCount": question_count}


def question(q: Question, has_blueprint: bool) -> Json:
    return {"id": q.id, "number": q.number, "text": q.text, "maxMarks": q.max_marks, "hasBlueprint": has_blueprint}


def blueprint(b: Blueprint) -> Json:
    return {"questionId": b.question.id, "modelAnswer": b.model_answer, "sourceFileName": b.source_file_name,
            "concepts": [{"id": c.id, "name": c.name, "keywords": split_keywords(c.keywords), "weight": c.weight}
                         for c in b.concepts]}


def submission(s: Submission, evaluation_id: Optional[int]) -> Json:
    return {"id": s.id, "examId": s.exam.id, "examTitle": s.exam.title, "studentId": s.student.id,
            "studentName": s.student.user.full_name, "rollNumber": s.student.roll_number,
            "fileName": s.original_file_name, "status": s.status, "uploadedAt": iso(s.uploaded_at),
            "errorMessage": s.error_message, "ocrConfidence": s.ocr_confidence, "evaluationId": evaluation_id}


def summary(ev: Evaluation) -> Json:
    s = ev.submission
    e = s.exam
    return {"id": ev.id, "submissionId": s.id, "examId": e.id, "examTitle": e.title, "subjectId": e.subject.id,
            "subjectName": e.subject.name, "studentId": s.student.id, "studentName": s.student.user.full_name,
            "rollNumber": s.student.roll_number, "status": ev.status, "maxTotal": ev.max_total,
            "aiTotal": ev.ai_total, "finalTotal": ev.final_total, "percentage": pct(ev.final_total, ev.max_total),
            "evaluatedAt": iso(ev.evaluated_at), "finalizedAt": iso(ev.finalized_at)}


def question_evaluation(q: QuestionEvaluation) -> Json:
    return {
        "id": q.id, "questionId": q.question.id, "questionNumber": q.question_number,
        "questionText": q.question.text, "answerText": q.answer_text, "answerFound": q.answer_found,
        "maxMarks": q.max_marks, "aiMarks": q.ai_marks, "finalMarks": q.final_marks,
        "effectiveMarks": q.effective_marks(), "confidence": q.confidence, "similarity": q.similarity,
        "conceptCoverage": q.concept_coverage, "matchedConcepts": q.matched_concepts,
        "missingConcepts": q.missing_concepts, "reviewed": q.reviewed,
        "mistakes": [{"id": m.id, "type": m.type, "description": m.description, "snippet": m.snippet,
                      "startOffset": m.start_offset, "endOffset": m.end_offset, "suggestion": m.suggestion}
                     for m in q.mistakes],
        "feedback": [{"id": f.id, "source": f.source, "text": f.text, "createdAt": iso(f.created_at)}
                     for f in q.feedbacks]}


def detail(ev: Evaluation) -> Json:
    return {"summary": summary(ev), "embeddingBackend": ev.embedding_backend,
            "reviewedBy": ev.reviewed_by.full_name if ev.reviewed_by else None,
            "questions": [question_evaluation(q) for q in ev.question_evaluations]}

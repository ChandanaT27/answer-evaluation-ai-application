from typing import List, Optional

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import ai_client, mapper
from ..errors import ApiException
from ..models import (Blueprint, BlueprintConcept, Evaluation, EvaluationStatus, Exam, Question, Subject, Submission,
                      User)
from ..schemas import BlueprintRequest, ExamRequest, QuestionRequest, SubjectRequest
from ..security import Principal
from ..storage import storage
from . import access, audit
from .common import contains, in_memory_page, norm, paginate


# ---------------------------------------------------------------- subjects
def published_exams_for_student(db: Session, student_id: int, subject_id: Optional[int]) -> List[Exam]:
    """Exams in which the given student has a finalized (published) evaluation."""
    stmt = (select(Exam).join(Submission, Submission.exam_id == Exam.id)
            .join(Evaluation, Evaluation.submission_id == Submission.id)
            .where(Submission.student_id == student_id, Evaluation.status == EvaluationStatus.FINALIZED.value))
    if subject_id is not None:
        stmt = stmt.where(Exam.subject_id == subject_id)
    return list(db.scalars(stmt.order_by(Exam.created_at.desc(), Exam.id.desc())).unique().all())


def exam_count_for_subject(db: Session, subject_id: int) -> int:
    return db.scalar(select(func.count()).select_from(Exam).where(Exam.subject_id == subject_id)) or 0


def list_subjects(db: Session, user: Principal, q: Optional[str], active_only: bool, page: int, size: int) -> dict:
    size = min(size, 200)
    needle = norm(q)
    if user.is_student:
        # students only see subjects in which they have published results
        student = access.current_student(db, user)
        seen, subjects = set(), []
        for e in published_exams_for_student(db, student.id, None):
            s = e.subject
            if s.id in seen or (needle and needle.lower() not in s.name.lower()):
                continue
            seen.add(s.id)
            subjects.append(s)
        subjects.sort(key=lambda s: s.name)
        return in_memory_page(subjects, page, size, lambda s: mapper.subject(s, 0))
    stmt = select(Subject)
    if needle:
        stmt = stmt.where(contains(Subject.name, needle) | contains(Subject.code, needle))
    if active_only:
        stmt = stmt.where(Subject.active.is_(True))
    return paginate(db, stmt.order_by(Subject.name, Subject.id), page, size,
                    lambda s: mapper.subject(s, exam_count_for_subject(db, s.id)))


def _subject_code_exists(db: Session, code: str) -> bool:
    return db.scalar(select(func.count()).select_from(Subject).where(func.lower(Subject.code) == code.lower())) > 0


def _apply_subject(s: Subject, r: SubjectRequest) -> None:
    s.name = r.name.strip()
    s.code = r.code.strip().upper()
    s.description = r.description
    if r.active is not None:
        s.active = r.active


def _find_subject(db: Session, subject_id: int) -> Subject:
    s = db.get(Subject, subject_id)
    if s is None:
        raise ApiException.not_found("Subject")
    return s


def _assert_can_modify_subject(user: Principal, s: Subject) -> None:
    if user.is_admin:
        return
    if s.created_by is not None and s.created_by.id == user.id:
        return
    raise ApiException.forbidden("Only the creator or an administrator can modify this subject")


def create_subject(db: Session, user: Principal, r: SubjectRequest) -> dict:
    if _subject_code_exists(db, r.code):
        raise ApiException.conflict("Subject code already exists")
    s = Subject()
    _apply_subject(s, r)
    s.created_by = db.get(User, user.id)
    db.add(s)
    db.flush()
    audit.log(db, user, "SUBJECT_CREATED", "Subject", s.id, s.code)
    db.commit()
    return mapper.subject(s, 0)


def update_subject(db: Session, user: Principal, subject_id: int, r: SubjectRequest) -> dict:
    s = _find_subject(db, subject_id)
    _assert_can_modify_subject(user, s)
    if s.code.lower() != r.code.lower() and _subject_code_exists(db, r.code):
        raise ApiException.conflict("Subject code already exists")
    _apply_subject(s, r)
    audit.log(db, user, "SUBJECT_UPDATED", "Subject", subject_id, s.code)
    db.commit()
    return mapper.subject(s, exam_count_for_subject(db, subject_id))


def delete_subject(db: Session, user: Principal, subject_id: int) -> None:
    s = _find_subject(db, subject_id)
    _assert_can_modify_subject(user, s)
    if exam_count_for_subject(db, subject_id) > 0:
        raise ApiException.conflict("Subject has exams; deactivate it instead of deleting")
    code = s.code
    db.delete(s)
    db.flush()
    audit.log(db, user, "SUBJECT_DELETED", "Subject", subject_id, code)
    db.commit()


# ------------------------------------------------------------------- exams
def find_exam(db: Session, exam_id: int) -> Exam:
    e = db.get(Exam, exam_id)
    if e is None:
        raise ApiException.not_found("Exam")
    return e


def questions_of(db: Session, exam_id: int) -> List[Question]:
    return list(db.scalars(select(Question).where(Question.exam_id == exam_id).order_by(Question.number)).all())


def exam_dto(db: Session, e: Exam) -> dict:
    qs = questions_of(db, e.id)
    return mapper.exam(e, sum(q.max_marks for q in qs), len(qs))


def list_exams(db: Session, user: Principal, subject_id: Optional[int], q: Optional[str], page: int,
               size: int) -> dict:
    size = min(size, 100)
    needle = norm(q)
    if user.is_student:
        student = access.current_student(db, user)
        exams = [e for e in published_exams_for_student(db, student.id, subject_id)
                 if not needle or needle.lower() in e.title.lower()]
        return in_memory_page(exams, page, size, lambda e: exam_dto(db, e))
    stmt = select(Exam)
    if user.is_teacher:
        stmt = stmt.where(Exam.teacher_id == access.current_teacher(db, user).id)
    if subject_id is not None:
        stmt = stmt.where(Exam.subject_id == subject_id)
    if needle:
        stmt = stmt.where(contains(Exam.title, needle))
    return paginate(db, stmt.order_by(Exam.created_at.desc(), Exam.id.desc()), page, size, lambda e: exam_dto(db, e))


def get_exam(db: Session, user: Principal, exam_id: int) -> dict:
    e = find_exam(db, exam_id)
    access.assert_exam_manage(user, e)
    return exam_dto(db, e)


def _apply_exam(e: Exam, r: ExamRequest, s: Subject) -> None:
    e.title = r.title.strip()
    e.subject = s
    e.exam_date = r.examDate
    e.instructions = r.instructions


def create_exam(db: Session, user: Principal, r: ExamRequest) -> dict:
    s = _find_subject(db, r.subjectId)
    if not s.active:
        raise ApiException.bad_request("Subject is inactive")
    e = Exam()
    e.teacher = access.current_teacher(db, user)
    _apply_exam(e, r, s)
    db.add(e)
    db.flush()
    audit.log(db, user, "EXAM_CREATED", "Exam", e.id, e.title)
    db.commit()
    return exam_dto(db, e)


def update_exam(db: Session, user: Principal, exam_id: int, r: ExamRequest) -> dict:
    e = find_exam(db, exam_id)
    access.assert_exam_manage(user, e)
    _apply_exam(e, r, _find_subject(db, r.subjectId))
    audit.log(db, user, "EXAM_UPDATED", "Exam", exam_id, e.title)
    db.commit()
    return exam_dto(db, e)


def delete_exam(db: Session, user: Principal, exam_id: int) -> None:
    e = find_exam(db, exam_id)
    access.assert_exam_manage(user, e)
    paper, title = e.question_paper_path, e.title
    db.delete(e)
    db.flush()
    audit.log(db, user, "EXAM_DELETED", "Exam", exam_id, title)
    db.commit()
    storage.delete_quietly(paper)


def upload_question_paper(db: Session, user: Principal, exam_id: int, file: UploadFile) -> dict:
    e = find_exam(db, exam_id)
    access.assert_exam_manage(user, e)
    f = storage.store(file, "question-papers")
    old = e.question_paper_path
    e.question_paper_path = f.relative_path
    e.question_paper_name = f.original_name
    audit.log(db, user, "QUESTION_PAPER_UPLOADED", "Exam", exam_id, f.original_name)
    db.commit()
    storage.delete_quietly(old)
    return exam_dto(db, e)


def question_paper(db: Session, user: Principal, exam_id: int):
    e = find_exam(db, exam_id)
    access.assert_exam_manage(user, e)
    if e.question_paper_path is None:
        raise ApiException.not_found("Question paper")
    return storage.resolve(e.question_paper_path), e.question_paper_name


# -------------------------------------------------- questions & blueprints
def find_question(db: Session, question_id: int) -> Question:
    q = db.get(Question, question_id)
    if q is None:
        raise ApiException.not_found("Question")
    return q


def blueprint_of(db: Session, question_id: int) -> Optional[Blueprint]:
    return db.scalar(select(Blueprint).where(Blueprint.question_id == question_id))


def list_questions(db: Session, user: Principal, exam_id: int) -> List[dict]:
    access.assert_exam_manage(user, find_exam(db, exam_id))
    return [mapper.question(q, blueprint_of(db, q.id) is not None) for q in questions_of(db, exam_id)]


def _question_exists(db: Session, exam_id: int, number: int) -> bool:
    return db.scalar(select(func.count()).select_from(Question)
                     .where(Question.exam_id == exam_id, Question.number == number)) > 0


def create_question(db: Session, user: Principal, exam_id: int, r: QuestionRequest) -> dict:
    exam = find_exam(db, exam_id)
    access.assert_exam_manage(user, exam)
    number = r.number if r.number is not None else max([q.number for q in questions_of(db, exam_id)] or [0]) + 1
    if _question_exists(db, exam_id, number):
        raise ApiException.conflict(f"Question {number} already exists in this exam")
    q = Question(exam=exam, number=number, text=r.text.strip(), max_marks=r.maxMarks)
    db.add(q)
    db.flush()
    audit.log(db, user, "QUESTION_CREATED", "Question", q.id, f"Exam {exam_id} Q{number}")
    db.commit()
    return mapper.question(q, False)


def update_question(db: Session, user: Principal, question_id: int, r: QuestionRequest) -> dict:
    q = find_question(db, question_id)
    access.assert_exam_manage(user, q.exam)
    if r.number is not None and r.number != q.number:
        if _question_exists(db, q.exam_id, r.number):
            raise ApiException.conflict(f"Question {r.number} already exists in this exam")
        q.number = r.number
    q.text = r.text.strip()
    q.max_marks = r.maxMarks
    audit.log(db, user, "QUESTION_UPDATED", "Question", question_id)
    db.commit()
    return mapper.question(q, blueprint_of(db, question_id) is not None)


def delete_question(db: Session, user: Principal, question_id: int) -> None:
    q = find_question(db, question_id)
    access.assert_exam_manage(user, q.exam)
    b = blueprint_of(db, question_id)
    if b is not None:
        db.delete(b)
    db.delete(q)
    db.flush()
    audit.log(db, user, "QUESTION_DELETED", "Question", question_id)
    db.commit()


def get_blueprint(db: Session, user: Principal, question_id: int) -> dict:
    q = find_question(db, question_id)
    access.assert_exam_manage(user, q.exam)
    b = blueprint_of(db, question_id)
    return mapper.blueprint(b) if b else {"questionId": question_id, "modelAnswer": "", "sourceFileName": None,
                                          "concepts": []}


def _blueprint_for(db: Session, q: Question) -> Blueprint:
    b = blueprint_of(db, q.id)
    if b is None:
        b = Blueprint(question=q)
        db.add(b)
    return b


def save_blueprint(db: Session, user: Principal, question_id: int, r: BlueprintRequest) -> dict:
    q = find_question(db, question_id)
    access.assert_exam_manage(user, q.exam)
    has_text = bool(r.modelAnswer and r.modelAnswer.strip())
    has_concepts = bool(r.concepts)
    if not has_text and not has_concepts:
        raise ApiException.bad_request("Provide a model answer and/or at least one concept")
    b = _blueprint_for(db, q)
    b.model_answer = (r.modelAnswer or "").strip()
    b.concepts = []
    for c in (r.concepts or []):
        kws = [k.strip().replace(",", " ") for k in (c.keywords or []) if k.strip()]
        b.concepts.append(BlueprintConcept(name=c.name.strip(), keywords=",".join(kws),
                                           weight=c.weight if c.weight is not None else 1.0))
    db.flush()
    audit.log(db, user, "BLUEPRINT_SAVED", "Question", question_id)
    db.commit()
    return mapper.blueprint(b)


def upload_blueprint_file(db: Session, user: Principal, question_id: int, file: UploadFile) -> dict:
    """Uploads a model-answer file (PDF/image/text), runs OCR, and stores the text as the model answer."""
    q = find_question(db, question_id)
    access.assert_exam_manage(user, q.exam)
    f = storage.store(file, "blueprints")
    try:
        ocr = ai_client.ocr(storage.resolve(f.relative_path), f.original_name)
    finally:
        storage.delete_quietly(f.relative_path)
    text = (ocr.get("text") or "").strip()
    if not text:
        raise ApiException.bad_request("No text could be extracted from the uploaded file")
    b = _blueprint_for(db, q)
    b.model_answer = text
    b.source_file_name = f.original_name
    db.flush()
    audit.log(db, user, "BLUEPRINT_UPLOADED", "Question", question_id, f.original_name)
    db.commit()
    return mapper.blueprint(b)

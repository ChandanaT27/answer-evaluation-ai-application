from datetime import datetime, timezone
from typing import List, Optional

from fastapi import UploadFile
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import mapper
from ..errors import ApiException
from ..models import Evaluation, EvaluationStatus, Student, StudentAnswer, Submission, SubmissionStatus
from ..security import Principal
from ..storage import storage
from . import access, audit
from .catalog import find_exam


def evaluation_of(db: Session, submission_id: int) -> Optional[Evaluation]:
    return db.scalar(select(Evaluation).where(Evaluation.submission_id == submission_id))


def dto(db: Session, s: Submission) -> dict:
    ev = evaluation_of(db, s.id)
    return mapper.submission(s, ev.id if ev else None)


def find(db: Session, submission_id: int) -> Submission:
    s = db.get(Submission, submission_id)
    if s is None:
        raise ApiException.not_found("Submission")
    return s


def _drop_results(db: Session, submission_id: int) -> None:
    ev = evaluation_of(db, submission_id)
    if ev is not None:
        db.delete(ev)
    db.execute(delete(StudentAnswer).where(StudentAnswer.submission_id == submission_id))
    db.flush()


def list_for_exam(db: Session, user: Principal, exam_id: int) -> List[dict]:
    access.assert_exam_manage(user, find_exam(db, exam_id))
    rows = db.scalars(select(Submission).where(Submission.exam_id == exam_id)
                      .order_by(Submission.uploaded_at.desc(), Submission.id.desc())).all()
    return [dto(db, s) for s in rows]


def upload(db: Session, user: Principal, exam_id: int, student_id: int, file: Optional[UploadFile]) -> dict:
    exam = find_exam(db, exam_id)
    access.assert_exam_manage(user, exam)
    student = db.get(Student, student_id)
    if student is None:
        raise ApiException.not_found("Student")
    existing = db.scalar(select(Submission).where(Submission.exam_id == exam_id,
                                                  Submission.student_id == student_id))
    if existing is not None:
        ev = evaluation_of(db, existing.id)
        if ev is not None and ev.status == EvaluationStatus.FINALIZED.value:
            raise ApiException.conflict("A finalized evaluation exists; delete it before re-uploading")
        if existing.status == SubmissionStatus.EVALUATING.value:
            raise ApiException.conflict("Evaluation in progress for this submission")
    stored = storage.store(file, "answer-sheets")
    s = existing if existing is not None else Submission()
    old_path = existing.file_path if existing is not None else None
    s.exam = exam
    s.student = student
    s.uploaded_by = access.current_teacher_or_none(db, user)
    s.file_path = stored.relative_path
    s.original_file_name = stored.original_name
    s.content_type = stored.content_type
    s.status = SubmissionStatus.UPLOADED.value
    s.ocr_text = None
    s.ocr_confidence = None
    s.error_message = None
    s.uploaded_at = datetime.now(timezone.utc)
    db.add(s)
    db.flush()
    if existing is not None:
        _drop_results(db, s.id)  # a replaced sheet invalidates previous AI results
    audit.log(db, user, "SUBMISSION_UPLOADED", "Submission", s.id, f"Exam {exam_id}, student {student_id}")
    db.commit()
    if old_path:
        storage.delete_quietly(old_path)
    return dto(db, s)


def get(db: Session, user: Principal, submission_id: int) -> dict:
    s = find(db, submission_id)
    access.assert_exam_manage(user, s.exam)
    return dto(db, s)


def delete_submission(db: Session, user: Principal, submission_id: int) -> None:
    s = find(db, submission_id)
    access.assert_exam_manage(user, s.exam)
    path = s.file_path
    _drop_results(db, submission_id)
    db.delete(s)
    audit.log(db, user, "SUBMISSION_DELETED", "Submission", submission_id, None)
    db.commit()
    storage.delete_quietly(path)


def file_of(db: Session, user: Principal, submission_id: int):
    """Returns (path, original_name, content_type)."""
    s = find(db, submission_id)
    if user.is_student:
        ev = evaluation_of(db, submission_id)
        own = s.student.user_id == user.id
        if not own or ev is None or ev.status != EvaluationStatus.FINALIZED.value:
            raise ApiException.forbidden("You can only view your own published answer sheet")
    else:
        access.assert_exam_manage(user, s.exam)
    return storage.resolve(s.file_path), s.original_file_name, s.content_type

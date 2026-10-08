from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import ApiException
from ..models import Evaluation, EvaluationStatus, Exam, Student, Teacher
from ..security import Principal


def current_teacher_or_none(db: Session, user: Principal) -> Optional[Teacher]:
    return db.scalar(select(Teacher).where(Teacher.user_id == user.id))


def current_teacher(db: Session, user: Principal) -> Teacher:
    t = current_teacher_or_none(db, user)
    if t is None:
        raise ApiException.forbidden("Teacher profile required")
    return t


def current_student(db: Session, user: Principal) -> Student:
    s = db.scalar(select(Student).where(Student.user_id == user.id))
    if s is None:
        raise ApiException.forbidden("Student profile required")
    return s


def assert_exam_manage(user: Principal, exam: Exam) -> None:
    """Admins may access everything; teachers only exams they own."""
    if user.is_admin:
        return
    if user.is_teacher and exam.teacher.user_id == user.id:
        return
    raise ApiException.forbidden("You do not own this exam")


def assert_evaluation_view(user: Principal, ev: Evaluation) -> None:
    """Teacher/admin view of an evaluation, or the owning student once it is finalized."""
    s = ev.submission
    if user.is_student:
        own = s.student.user_id == user.id
        if not own or ev.status != EvaluationStatus.FINALIZED.value:
            raise ApiException.forbidden("You can only view your own published results")
        return
    assert_exam_manage(user, s.exam)


def assert_staff_evaluation(user: Principal, ev: Evaluation) -> None:
    if user.is_student:
        raise ApiException.forbidden("Not allowed")
    assert_exam_manage(user, ev.submission.exam)

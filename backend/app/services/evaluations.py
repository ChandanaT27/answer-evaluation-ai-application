from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .. import mapper, ai_client  # noqa: F401
from ..errors import ApiException
from ..models import (Blueprint, Evaluation, EvaluationHistory, EvaluationStatus, Exam, Feedback, Question,
                      QuestionEvaluation, Student, StudentAnswer, Subject, Submission, SubmissionStatus, User)
from ..schemas import ReviewRequest
from ..security import Principal
from . import access, audit, runner
from .common import contains, norm, paginate
from .submissions import dto as submission_dto, evaluation_of, find as find_submission


def find(db: Session, evaluation_id: int) -> Evaluation:
    ev = db.get(Evaluation, evaluation_id)
    if ev is None:
        raise ApiException.not_found("Evaluation")
    return ev


def start(db: Session, user: Principal, submission_id: int) -> dict:
    sub = find_submission(db, submission_id)
    access.assert_exam_manage(user, sub.exam)
    if sub.status == SubmissionStatus.EVALUATING.value:
        raise ApiException.conflict("Evaluation already in progress")
    ev = evaluation_of(db, submission_id)
    if ev is not None and ev.status == EvaluationStatus.FINALIZED.value:
        raise ApiException.conflict("Evaluation is finalized; delete it first to re-evaluate")
    qs = list(db.scalars(select(Question).where(Question.exam_id == sub.exam_id).order_by(Question.number)))
    if not qs:
        raise ApiException.bad_request("The exam has no questions")
    missing: List[int] = []
    for q in qs:
        b = db.scalar(select(Blueprint).where(Blueprint.question_id == q.id))
        ok = b is not None and ((b.model_answer and b.model_answer.strip()) or len(b.concepts) > 0)
        if not ok:
            missing.append(q.number)
    if missing:
        raise ApiException.bad_request(f"Blueprint missing for question(s): {missing}")
    sub.status = SubmissionStatus.EVALUATING.value
    sub.error_message = None
    audit.log(db, user, "EVALUATION_STARTED", "Submission", submission_id, None)
    db.commit()
    result = mapper.submission(sub, None)
    runner.submit(submission_id, user.id, user.username)
    return result


def search(db: Session, user: Principal, exam_id, subject_id, student_id, status, from_date: Optional[date],
           to_date: Optional[date], q: Optional[str], page: int, size: int) -> dict:
    teacher_id = None
    if user.is_student:
        student_id = access.current_student(db, user).id
        status = EvaluationStatus.FINALIZED.value
    elif user.is_teacher:
        teacher_id = access.current_teacher(db, user).id
    start_dt = (datetime(from_date.year, from_date.month, from_date.day, tzinfo=timezone.utc)
                if from_date else datetime(1970, 1, 1, tzinfo=timezone.utc))
    end_dt = (datetime(to_date.year, to_date.month, to_date.day, tzinfo=timezone.utc) + timedelta(days=1)
              - timedelta(milliseconds=1)) if to_date else datetime(9999, 1, 1, tzinfo=timezone.utc)
    stmt = (select(Evaluation).join(Submission, Evaluation.submission_id == Submission.id)
            .join(Exam, Submission.exam_id == Exam.id).join(Student, Submission.student_id == Student.id)
            .join(User, Student.user_id == User.id)
            .where(Evaluation.evaluated_at >= start_dt, Evaluation.evaluated_at <= end_dt))
    if teacher_id is not None:
        stmt = stmt.where(Exam.teacher_id == teacher_id)
    if student_id is not None:
        stmt = stmt.where(Submission.student_id == student_id)
    if exam_id is not None:
        stmt = stmt.where(Submission.exam_id == exam_id)
    if subject_id is not None:
        stmt = stmt.where(Exam.subject_id == subject_id)
    if status is not None:
        stmt = stmt.where(Evaluation.status == status)
    needle = norm(q)
    if needle:
        stmt = stmt.where(contains(User.full_name, needle) | contains(Student.roll_number, needle)
                          | contains(Exam.title, needle))
    return paginate(db, stmt.order_by(Evaluation.evaluated_at.desc(), Evaluation.id.desc()), page,
                    min(size, 100), mapper.summary)


def get(db: Session, user: Principal, evaluation_id: int) -> dict:
    ev = find(db, evaluation_id)
    access.assert_evaluation_view(user, ev)
    return mapper.detail(ev)


def _recalc(ev: Evaluation) -> None:
    ev.final_total = sum(q.effective_marks() for q in ev.question_evaluations)


def _record(db: Session, user: Principal, ev: Evaluation, q_no, action: str, old, new, note=None) -> None:
    db.add(EvaluationHistory(evaluation_id=ev.id, submission_id=ev.submission_id, question_number=q_no,
                             action=action, old_marks=old, new_marks=new, note=note[:1000] if note else note,
                             changed_by_id=user.id, changed_by_name=user.username))


def review(db: Session, user: Principal, evaluation_id: int, qe_id: int, r: ReviewRequest) -> dict:
    ev = find(db, evaluation_id)
    access.assert_staff_evaluation(user, ev)
    qe = next((x for x in ev.question_evaluations if x.id == qe_id), None)
    if qe is None:
        raise ApiException.not_found("Question evaluation")
    if r.finalMarks > qe.max_marks:
        raise ApiException.bad_request(f"Marks cannot exceed the maximum of {qe.max_marks}")
    old = qe.effective_marks()
    qe.final_marks = r.finalMarks
    qe.reviewed = True
    if r.comment and r.comment.strip():
        qe.feedbacks.append(Feedback(source="TEACHER", text=r.comment.strip()))
    _recalc(ev)
    if ev.status == EvaluationStatus.AI_COMPLETED.value:
        ev.status = EvaluationStatus.UNDER_REVIEW.value
    _record(db, user, ev, qe.question_number, "MARKS_OVERRIDDEN", old, r.finalMarks, r.comment)
    audit.log(db, user, "MARKS_OVERRIDDEN", "Evaluation", evaluation_id,
              f"Q{qe.question_number}: {old} -> {r.finalMarks}")
    db.commit()
    return mapper.detail(ev)


def finalize(db: Session, user: Principal, evaluation_id: int) -> dict:
    ev = find(db, evaluation_id)
    access.assert_staff_evaluation(user, ev)
    _recalc(ev)
    for q in ev.question_evaluations:
        q.reviewed = True
    ev.status = EvaluationStatus.FINALIZED.value
    ev.finalized_at = datetime.now(timezone.utc)
    ev.reviewed_by = db.get(User, user.id)
    _record(db, user, ev, None, "FINALIZED", ev.ai_total, ev.final_total)
    audit.log(db, user, "EVALUATION_FINALIZED", "Evaluation", evaluation_id,
              f"Total {ev.final_total}/{ev.max_total}")
    db.commit()
    return mapper.detail(ev)


def reopen(db: Session, user: Principal, evaluation_id: int) -> dict:
    ev = find(db, evaluation_id)
    access.assert_staff_evaluation(user, ev)
    if ev.status != EvaluationStatus.FINALIZED.value:
        raise ApiException.bad_request("Evaluation is not finalized")
    ev.status = EvaluationStatus.UNDER_REVIEW.value
    ev.finalized_at = None
    _record(db, user, ev, None, "REOPENED", ev.final_total, ev.final_total)
    audit.log(db, user, "EVALUATION_REOPENED", "Evaluation", evaluation_id, None)
    db.commit()
    return mapper.detail(ev)


def delete_evaluation(db: Session, user: Principal, evaluation_id: int) -> None:
    ev = find(db, evaluation_id)
    access.assert_staff_evaluation(user, ev)
    sub = ev.submission
    _record(db, user, ev, None, "DELETED", ev.final_total, None)
    db.delete(ev)
    db.execute(delete(StudentAnswer).where(StudentAnswer.submission_id == sub.id))
    sub.status = SubmissionStatus.UPLOADED.value
    audit.log(db, user, "EVALUATION_DELETED", "Evaluation", evaluation_id, f"Submission {sub.id}")
    db.commit()


def history(db: Session, user: Principal, evaluation_id: int) -> List[dict]:
    ev = find(db, evaluation_id)
    access.assert_staff_evaluation(user, ev)
    rows = db.scalars(select(EvaluationHistory).where(EvaluationHistory.evaluation_id == evaluation_id)
                      .order_by(EvaluationHistory.changed_at.desc(), EvaluationHistory.id.desc()))
    return [{"id": h.id, "questionNumber": h.question_number, "action": h.action, "oldMarks": h.old_marks,
             "newMarks": h.new_marks, "note": h.note, "changedBy": h.changed_by_name,
             "changedAt": mapper.iso(h.changed_at)} for h in rows]


def teacher_stats(db: Session, user: Principal) -> dict:
    t = access.current_teacher(db, user)
    evs = list(db.scalars(select(Evaluation).join(Submission, Evaluation.submission_id == Submission.id)
                          .join(Exam, Submission.exam_id == Exam.id).where(Exam.teacher_id == t.id)))
    finalized = sum(1 for e in evs if e.status == EvaluationStatus.FINALIZED.value)
    pcts = [e.final_total / e.max_total * 100 for e in evs if e.max_total > 0]
    avg = sum(pcts) / len(pcts) if pcts else 0.0
    exams = db.scalar(select(func.count()).select_from(Exam).where(Exam.teacher_id == t.id)) or 0
    subs = db.scalar(select(func.count()).select_from(Submission).join(Exam, Submission.exam_id == Exam.id)
                     .where(Exam.teacher_id == t.id)) or 0
    return {"exams": exams, "submissions": subs, "evaluations": len(evs), "pendingReview": len(evs) - finalized,
            "finalized": finalized, "averagePercentage": mapper.round2(avg)}


def performance(db: Session, user: Principal) -> dict:
    s = access.current_student(db, user)
    evs = list(db.scalars(select(Evaluation).join(Submission, Evaluation.submission_id == Submission.id)
                          .where(Submission.student_id == s.id, Evaluation.status == EvaluationStatus.FINALIZED.value)
                          .order_by(Evaluation.finalized_at.asc(), Evaluation.id.asc())))
    perf = [{"evaluationId": e.id, "examTitle": e.submission.exam.title,
             "subjectName": e.submission.exam.subject.name, "percentage": mapper.pct(e.final_total, e.max_total),
             "marks": e.final_total, "maxMarks": e.max_total, "date": mapper.iso(e.finalized_at)} for e in evs]
    by_subject: dict = {}
    for p in perf:
        by_subject.setdefault(p["subjectName"], []).append(p)
    subjects = [{"subjectName": name, "averagePercentage": mapper.round2(sum(x["percentage"] for x in items) / len(items)),
                 "exams": len(items)} for name, items in by_subject.items()]
    overall = sum(p["percentage"] for p in perf) / len(perf) if perf else 0.0
    return {"exams": perf, "subjects": subjects, "overallPercentage": mapper.round2(overall)}

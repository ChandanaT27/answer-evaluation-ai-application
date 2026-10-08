from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import EvaluationStatus, Permission
from ..schemas import ReviewRequest
from ..security import Principal, current_principal, require_permission, require_role
from ..services import evaluations, reports, submissions
from .files import inline

router = APIRouter()
Upload = Depends(require_permission(Permission.SUBMISSION_UPLOAD))
Run = Depends(require_permission(Permission.EVALUATION_RUN))
Review = Depends(require_permission(Permission.EVALUATION_REVIEW))
Staff = Depends(require_role("ADMIN", "TEACHER"))


@router.get("/exams/{exam_id}/submissions")
def list_submissions(exam_id: int, p: Principal = Upload, db: Session = Depends(get_db)):
    return submissions.list_for_exam(db, p, exam_id)


@router.post("/exams/{exam_id}/submissions", status_code=201)
def upload(exam_id: int, studentId: int = Form(...), file: UploadFile = File(...), p: Principal = Upload,
           db: Session = Depends(get_db)):
    return submissions.upload(db, p, exam_id, studentId, file)


@router.get("/submissions/{submission_id}")
def get_submission(submission_id: int, p: Principal = Upload, db: Session = Depends(get_db)):
    return submissions.get(db, p, submission_id)


@router.delete("/submissions/{submission_id}", status_code=204)
def delete_submission(submission_id: int, p: Principal = Upload, db: Session = Depends(get_db)):
    submissions.delete_submission(db, p, submission_id)
    return Response(status_code=204)


@router.get("/submissions/{submission_id}/file")
def submission_file(submission_id: int, p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    path, name, _ = submissions.file_of(db, p, submission_id)
    return inline(path, name)


@router.post("/submissions/{submission_id}/evaluate", status_code=202)
def evaluate(submission_id: int, p: Principal = Run, db: Session = Depends(get_db)):
    return evaluations.start(db, p, submission_id)


@router.get("/evaluations")
def search(examId: Optional[int] = None, subjectId: Optional[int] = None, studentId: Optional[int] = None,
           status: Optional[EvaluationStatus] = None, from_: Optional[date] = Query(None, alias="from"), to: Optional[date] = None,
           q: Optional[str] = None, page: int = 0, size: int = 20,
           p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    return evaluations.search(db, p, examId, subjectId, studentId, status.value if status else None,
                              from_, to, q, page, size)


@router.get("/evaluations/{evaluation_id}")
def get_evaluation(evaluation_id: int, p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    return evaluations.get(db, p, evaluation_id)


@router.put("/evaluations/{evaluation_id}/questions/{qe_id}")
def review(evaluation_id: int, qe_id: int, r: ReviewRequest, p: Principal = Review, db: Session = Depends(get_db)):
    return evaluations.review(db, p, evaluation_id, qe_id, r)


@router.post("/evaluations/{evaluation_id}/finalize")
def finalize(evaluation_id: int, p: Principal = Review, db: Session = Depends(get_db)):
    return evaluations.finalize(db, p, evaluation_id)


@router.post("/evaluations/{evaluation_id}/reopen")
def reopen(evaluation_id: int, p: Principal = Review, db: Session = Depends(get_db)):
    return evaluations.reopen(db, p, evaluation_id)


@router.delete("/evaluations/{evaluation_id}", status_code=204)
def delete_evaluation(evaluation_id: int, p: Principal = Depends(require_permission(Permission.EVALUATION_DELETE)),
                      db: Session = Depends(get_db)):
    evaluations.delete_evaluation(db, p, evaluation_id)
    return Response(status_code=204)


@router.get("/evaluations/{evaluation_id}/history")
def history(evaluation_id: int, p: Principal = Staff, db: Session = Depends(get_db)):
    return evaluations.history(db, p, evaluation_id)


@router.get("/evaluations/{evaluation_id}/report")
def report(evaluation_id: int, p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    data = reports.report(db, p, evaluation_id)
    return Response(content=data, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="inkgrade-report-{evaluation_id}.pdf"'})

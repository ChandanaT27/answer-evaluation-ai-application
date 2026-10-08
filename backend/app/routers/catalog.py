from typing import Optional

from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Permission
from ..schemas import BlueprintRequest, ExamRequest, QuestionRequest, SubjectRequest
from ..security import Principal, current_principal, require_permission, require_role
from ..services import catalog, evaluations, users
from .files import inline

router = APIRouter()
ExamMgr = Depends(require_permission(Permission.EXAM_MANAGE))
SubjectMgr = Depends(require_permission(Permission.SUBJECT_MANAGE))


@router.get("/subjects")
def subjects(q: Optional[str] = None, activeOnly: bool = False, page: int = 0, size: int = 50,
             p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    return catalog.list_subjects(db, p, q, activeOnly, page, size)


@router.post("/subjects", status_code=201)
def create_subject(r: SubjectRequest, p: Principal = SubjectMgr, db: Session = Depends(get_db)):
    return catalog.create_subject(db, p, r)


@router.put("/subjects/{subject_id}")
def update_subject(subject_id: int, r: SubjectRequest, p: Principal = SubjectMgr, db: Session = Depends(get_db)):
    return catalog.update_subject(db, p, subject_id, r)


@router.delete("/subjects/{subject_id}", status_code=204)
def delete_subject(subject_id: int, p: Principal = SubjectMgr, db: Session = Depends(get_db)):
    catalog.delete_subject(db, p, subject_id)
    return Response(status_code=204)


@router.get("/exams")
def exams(subjectId: Optional[int] = None, q: Optional[str] = None, page: int = 0, size: int = 20,
          p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    return catalog.list_exams(db, p, subjectId, q, page, size)


@router.get("/exams/{exam_id}")
def get_exam(exam_id: int, p: Principal = ExamMgr, db: Session = Depends(get_db)):
    return catalog.get_exam(db, p, exam_id)


@router.post("/exams", status_code=201)
def create_exam(r: ExamRequest, p: Principal = ExamMgr, db: Session = Depends(get_db)):
    return catalog.create_exam(db, p, r)


@router.put("/exams/{exam_id}")
def update_exam(exam_id: int, r: ExamRequest, p: Principal = ExamMgr, db: Session = Depends(get_db)):
    return catalog.update_exam(db, p, exam_id, r)


@router.delete("/exams/{exam_id}", status_code=204)
def delete_exam(exam_id: int, p: Principal = ExamMgr, db: Session = Depends(get_db)):
    catalog.delete_exam(db, p, exam_id)
    return Response(status_code=204)


@router.post("/exams/{exam_id}/question-paper")
def upload_paper(exam_id: int, file: UploadFile = File(...), p: Principal = ExamMgr, db: Session = Depends(get_db)):
    return catalog.upload_question_paper(db, p, exam_id, file)


@router.get("/exams/{exam_id}/question-paper")
def get_paper(exam_id: int, p: Principal = ExamMgr, db: Session = Depends(get_db)):
    path, name = catalog.question_paper(db, p, exam_id)
    return inline(path, name)


@router.get("/exams/{exam_id}/questions")
def list_questions(exam_id: int, p: Principal = ExamMgr, db: Session = Depends(get_db)):
    return catalog.list_questions(db, p, exam_id)


@router.post("/exams/{exam_id}/questions", status_code=201)
def create_question(exam_id: int, r: QuestionRequest, p: Principal = ExamMgr, db: Session = Depends(get_db)):
    return catalog.create_question(db, p, exam_id, r)


@router.put("/questions/{question_id}")
def update_question(question_id: int, r: QuestionRequest, p: Principal = ExamMgr, db: Session = Depends(get_db)):
    return catalog.update_question(db, p, question_id, r)


@router.delete("/questions/{question_id}", status_code=204)
def delete_question(question_id: int, p: Principal = ExamMgr, db: Session = Depends(get_db)):
    catalog.delete_question(db, p, question_id)
    return Response(status_code=204)


@router.get("/questions/{question_id}/blueprint")
def get_blueprint(question_id: int, p: Principal = ExamMgr, db: Session = Depends(get_db)):
    return catalog.get_blueprint(db, p, question_id)


@router.put("/questions/{question_id}/blueprint")
def save_blueprint(question_id: int, r: BlueprintRequest, p: Principal = ExamMgr, db: Session = Depends(get_db)):
    return catalog.save_blueprint(db, p, question_id, r)


@router.post("/questions/{question_id}/blueprint/upload")
def upload_blueprint(question_id: int, file: UploadFile = File(...), p: Principal = ExamMgr,
                     db: Session = Depends(get_db)):
    return catalog.upload_blueprint_file(db, p, question_id, file)


@router.get("/students")
def students(q: Optional[str] = None, page: int = 0, size: int = 20,
             _: Principal = Depends(require_role("ADMIN", "TEACHER")), db: Session = Depends(get_db)):
    return users.students(db, q, page, size)


@router.get("/teacher/stats")
def teacher_stats(p: Principal = Depends(require_role("TEACHER")), db: Session = Depends(get_db)):
    return evaluations.teacher_stats(db, p)


@router.get("/student/performance")
def student_performance(p: Principal = Depends(require_role("STUDENT")), db: Session = Depends(get_db)):
    return evaluations.performance(db, p)

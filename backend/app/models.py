import enum
from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import (BigInteger, Boolean, Date, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, BigIntPK, UTCDateTime


def now() -> datetime:
    return datetime.now(timezone.utc)


class RoleName(str, enum.Enum):
    ADMIN = "ADMIN"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"


class SubmissionStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    EVALUATING = "EVALUATING"
    EVALUATED = "EVALUATED"
    FAILED = "FAILED"


class EvaluationStatus(str, enum.Enum):
    """AI_COMPLETED -> UNDER_REVIEW (teacher edited) -> FINALIZED (visible to student)."""
    AI_COMPLETED = "AI_COMPLETED"
    UNDER_REVIEW = "UNDER_REVIEW"
    FINALIZED = "FINALIZED"


class MistakeType(str, enum.Enum):
    SPELLING = "SPELLING"
    GRAMMAR = "GRAMMAR"
    MISSING_CONCEPT = "MISSING_CONCEPT"
    INCORRECT_CONTENT = "INCORRECT_CONTENT"


class Permission:
    EXAM_MANAGE = "EXAM_MANAGE"
    SUBJECT_MANAGE = "SUBJECT_MANAGE"
    SUBMISSION_UPLOAD = "SUBMISSION_UPLOAD"
    EVALUATION_RUN = "EVALUATION_RUN"
    EVALUATION_REVIEW = "EVALUATION_REVIEW"
    EVALUATION_DELETE = "EVALUATION_DELETE"
    REPORT_DOWNLOAD = "REPORT_DOWNLOAD"
    ALL = [EXAM_MANAGE, SUBJECT_MANAGE, SUBMISSION_UPLOAD, EVALUATION_RUN, EVALUATION_REVIEW,
           EVALUATION_DELETE, REPORT_DOWNLOAD]


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("roles.id"), primary_key=True)
    permission: Mapped[str] = mapped_column(String(50), primary_key=True)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    permission_rows: Mapped[List[RolePermission]] = relationship(
        cascade="all, delete-orphan", lazy="selectin")

    @property
    def permissions(self) -> set:
        return {p.permission for p in self.permission_rows}

    def set_permissions(self, perms) -> None:
        wanted = set(perms)
        self.permission_rows = [p for p in self.permission_rows if p.permission in wanted]
        have = {p.permission for p in self.permission_rows}
        for p in sorted(wanted - have):
            self.permission_rows.append(RolePermission(permission=p))


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("roles.id"), nullable=False)
    role: Mapped[Role] = relationship(lazy="joined")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, default=now)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)


class Teacher(Base):
    __tablename__ = "teachers"
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True, nullable=False)
    user: Mapped[User] = relationship(lazy="joined")
    employee_id: Mapped[Optional[str]] = mapped_column(String(40))
    department: Mapped[Optional[str]] = mapped_column(String(80))


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True, nullable=False)
    user: Mapped[User] = relationship(lazy="joined")
    roll_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    class_name: Mapped[Optional[str]] = mapped_column(String(60))


class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"))
    created_by: Mapped[Optional[User]] = relationship()


class Exam(Base):
    __tablename__ = "exams"
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    subject_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("subjects.id"), nullable=False)
    subject: Mapped[Subject] = relationship()
    teacher_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("teachers.id"), nullable=False)
    teacher: Mapped[Teacher] = relationship()
    exam_date: Mapped[Optional[date]] = mapped_column(Date)
    instructions: Mapped[Optional[str]] = mapped_column(String(1000))
    question_paper_path: Mapped[Optional[str]] = mapped_column(String(255))
    question_paper_name: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, default=now)


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("exam_id", "number"),)
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("exams.id"), nullable=False)
    exam: Mapped[Exam] = relationship()
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    max_marks: Mapped[float] = mapped_column(Float, nullable=False)


class BlueprintConcept(Base):
    __tablename__ = "blueprint_concepts"
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    blueprint_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("blueprints.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    keywords: Mapped[Optional[str]] = mapped_column(String(1000))  # comma separated synonyms
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)


class Blueprint(Base):
    __tablename__ = "blueprints"
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("questions.id"), unique=True, nullable=False)
    question: Mapped[Question] = relationship()
    model_answer: Mapped[Optional[str]] = mapped_column(Text)
    source_file_name: Mapped[Optional[str]] = mapped_column(String(255))
    concepts: Mapped[List[BlueprintConcept]] = relationship(
        cascade="all, delete-orphan", order_by=BlueprintConcept.id)


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("exam_id", "student_id"),)
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("exams.id"), nullable=False)
    exam: Mapped[Exam] = relationship()
    student_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("students.id"), nullable=False)
    student: Mapped[Student] = relationship()
    uploaded_by_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("teachers.id"))
    uploaded_by: Mapped[Optional[Teacher]] = relationship()
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=SubmissionStatus.UPLOADED.value)
    ocr_text: Mapped[Optional[str]] = mapped_column(Text)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(Float)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000))
    uploaded_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, default=now)


class StudentAnswer(Base):
    __tablename__ = "student_answers"
    __table_args__ = (UniqueConstraint("submission_id", "question_id"),)
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("submissions.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("questions.id"), nullable=False)
    question: Mapped[Question] = relationship()
    answer_text: Mapped[Optional[str]] = mapped_column(Text)
    found: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Mistake(Base):
    __tablename__ = "mistakes"
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    question_evaluation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("question_evaluations.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    snippet: Mapped[Optional[str]] = mapped_column(String(1000))
    start_offset: Mapped[Optional[int]] = mapped_column(Integer)
    end_offset: Mapped[Optional[int]] = mapped_column(Integer)
    suggestion: Mapped[Optional[str]] = mapped_column(String(300))


class Feedback(Base):
    __tablename__ = "feedbacks"
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    question_evaluation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("question_evaluations.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False)  # AI | TEACHER
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, default=now)


class QeMatchedConcept(Base):
    __tablename__ = "qe_matched_concepts"
    question_evaluation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("question_evaluations.id"), primary_key=True)
    concept: Mapped[str] = mapped_column(String(200), primary_key=True)


class QeMissingConcept(Base):
    __tablename__ = "qe_missing_concepts"
    question_evaluation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("question_evaluations.id"), primary_key=True)
    concept: Mapped[str] = mapped_column(String(200), primary_key=True)


class QuestionEvaluation(Base):
    __tablename__ = "question_evaluations"
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    evaluation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("evaluations.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("questions.id"), nullable=False)
    question: Mapped[Question] = relationship()
    question_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    answer_text: Mapped[Optional[str]] = mapped_column(Text)
    answer_found: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_marks: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    ai_marks: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    final_marks: Mapped[Optional[float]] = mapped_column(Float)  # null until a teacher overrides
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    similarity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    concept_coverage: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    matched_rows: Mapped[List[QeMatchedConcept]] = relationship(cascade="all, delete-orphan")
    missing_rows: Mapped[List[QeMissingConcept]] = relationship(cascade="all, delete-orphan")
    mistakes: Mapped[List[Mistake]] = relationship(cascade="all, delete-orphan", order_by=Mistake.id)
    feedbacks: Mapped[List[Feedback]] = relationship(cascade="all, delete-orphan", order_by=Feedback.id)

    @property
    def matched_concepts(self) -> List[str]:
        return [r.concept for r in self.matched_rows]

    @property
    def missing_concepts(self) -> List[str]:
        return [r.concept for r in self.missing_rows]

    def effective_marks(self) -> float:
        return self.final_marks if self.final_marks is not None else self.ai_marks


class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("submissions.id"), unique=True, nullable=False)
    submission: Mapped[Submission] = relationship()
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=EvaluationStatus.AI_COMPLETED.value)
    max_total: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    ai_total: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    # sum of effective (teacher override, else AI) marks; refreshed on every review change
    final_total: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    embedding_backend: Mapped[Optional[str]] = mapped_column(String(255))
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, default=now)
    finalized_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"))
    reviewed_by: Mapped[Optional[User]] = relationship()
    question_evaluations: Mapped[List[QuestionEvaluation]] = relationship(
        cascade="all, delete-orphan", order_by=QuestionEvaluation.question_number)


class EvaluationHistory(Base):
    __tablename__ = "evaluation_history"
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    # plain id (not an FK) so history survives deletion of the evaluation
    evaluation_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    submission_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    question_number: Mapped[Optional[int]] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    old_marks: Mapped[Optional[float]] = mapped_column(Float)
    new_marks: Mapped[Optional[float]] = mapped_column(Float)
    note: Mapped[Optional[str]] = mapped_column(String(1000))
    changed_by_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    changed_by_name: Mapped[Optional[str]] = mapped_column(String(255))
    changed_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, default=now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_created_at", "created_at"),)
    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    username: Mapped[Optional[str]] = mapped_column(String(60))
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(60))
    entity_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    details: Mapped[Optional[str]] = mapped_column(String(1000))
    ip_address: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=now)

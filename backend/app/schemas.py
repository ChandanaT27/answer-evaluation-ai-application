import re
from datetime import date
from typing import Annotated, List, Optional, Set

from pydantic import AfterValidator, BaseModel, Field

from .models import RoleName


def _not_blank(v: str) -> str:
    if not v.strip():
        raise ValueError("must not be blank")
    return v


def _email(v: str) -> str:
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
        raise ValueError("must be a well-formed email address")
    return v


def _code(v: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", v):
        raise ValueError("letters, digits, - _ only")
    return v


def _username(v: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", v):
        raise ValueError("letters, digits, . _ - only")
    return v


NotBlank = Annotated[str, AfterValidator(_not_blank)]
Email = Annotated[str, AfterValidator(_not_blank), AfterValidator(_email)]


class LoginRequest(BaseModel):
    username: NotBlank
    password: NotBlank


class ChangePasswordRequest(BaseModel):
    currentPassword: NotBlank
    newPassword: NotBlank = Field(min_length=8, max_length=100)


class SubjectRequest(BaseModel):
    name: NotBlank = Field(max_length=120)
    code: Annotated[str, AfterValidator(_not_blank), AfterValidator(_code)] = Field(max_length=30)
    description: Optional[str] = Field(default=None, max_length=500)
    active: Optional[bool] = None


class ExamRequest(BaseModel):
    title: NotBlank = Field(max_length=160)
    subjectId: int
    examDate: Optional[date] = None
    instructions: Optional[str] = Field(default=None, max_length=1000)


class QuestionRequest(BaseModel):
    number: Optional[int] = Field(default=None, ge=1)
    text: NotBlank = Field(max_length=5000)
    maxMarks: float = Field(gt=0, le=1000)


class ConceptRequest(BaseModel):
    id: Optional[int] = None
    name: NotBlank = Field(max_length=160)
    keywords: Optional[List[Annotated[str, Field(max_length=100)]]] = None
    weight: Optional[float] = Field(default=None, gt=0, le=100)


class BlueprintRequest(BaseModel):
    modelAnswer: Optional[str] = Field(default=None, max_length=20000)
    concepts: Optional[List[ConceptRequest]] = None


class ReviewRequest(BaseModel):
    finalMarks: float = Field(ge=0)
    comment: Optional[str] = Field(default=None, max_length=2000)


class CreateUserRequest(BaseModel):
    username: Annotated[str, AfterValidator(_not_blank), AfterValidator(_username)] = Field(min_length=3, max_length=60)
    email: Email = Field(max_length=120)
    fullName: NotBlank = Field(max_length=120)
    password: NotBlank = Field(min_length=8, max_length=100)
    role: RoleName
    rollNumber: Optional[str] = Field(default=None, max_length=40)
    className: Optional[str] = Field(default=None, max_length=60)
    employeeId: Optional[str] = Field(default=None, max_length=40)
    department: Optional[str] = Field(default=None, max_length=80)


class UpdateUserRequest(BaseModel):
    email: Email = Field(max_length=120)
    fullName: NotBlank = Field(max_length=120)
    enabled: Optional[bool] = None
    rollNumber: Optional[str] = Field(default=None, max_length=40)
    className: Optional[str] = Field(default=None, max_length=60)
    employeeId: Optional[str] = Field(default=None, max_length=40)
    department: Optional[str] = Field(default=None, max_length=80)


class ResetPasswordRequest(BaseModel):
    newPassword: NotBlank = Field(min_length=8, max_length=100)


class UpdatePermissionsRequest(BaseModel):
    permissions: Set[str]

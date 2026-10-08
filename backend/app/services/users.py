from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import mapper
from ..errors import ApiException
from ..models import (AuditLog, Evaluation, EvaluationStatus, Exam, Permission, Role, RoleName, Student, Subject,
                      Submission, Teacher, User)
from ..schemas import CreateUserRequest, ResetPasswordRequest, UpdatePermissionsRequest, UpdateUserRequest
from ..security import Principal, hash_password
from . import audit
from .common import contains, norm, paginate


def _teacher_of(db: Session, user_id: int) -> Optional[Teacher]:
    return db.scalar(select(Teacher).where(Teacher.user_id == user_id))


def _student_of(db: Session, user_id: int) -> Optional[Student]:
    return db.scalar(select(Student).where(Student.user_id == user_id))


def dto(db: Session, u: User) -> dict:
    return mapper.user(u, _student_of(db, u.id), _teacher_of(db, u.id))


def count_by_role(db: Session, role: RoleName) -> int:
    return db.scalar(select(func.count()).select_from(User).join(Role, User.role_id == Role.id)
                     .where(Role.name == role.value)) or 0


def _email_exists(db: Session, email: str) -> bool:
    return db.scalar(select(func.count()).select_from(User).where(func.lower(User.email) == email.lower())) > 0


def _roll_exists(db: Session, roll: str) -> bool:
    return db.scalar(select(func.count()).select_from(Student)
                     .where(func.lower(Student.roll_number) == roll.lower())) > 0


def get_user(db: Session, user_id: int) -> User:
    u = db.get(User, user_id)
    if u is None:
        raise ApiException.not_found("User")
    return u


def list_users(db: Session, role: Optional[RoleName], q: Optional[str], page: int, size: int) -> dict:
    size = min(size, 100)
    stmt = select(User).join(Role, User.role_id == Role.id)
    if role is not None:
        stmt = stmt.where(Role.name == role.value)
    needle = norm(q)
    if needle:
        stmt = stmt.where(contains(User.username, needle) | contains(User.full_name, needle)
                          | contains(User.email, needle))
    return paginate(db, stmt.order_by(User.full_name, User.id), page, size, lambda u: dto(db, u))


def create_user(db: Session, actor: Principal, r: CreateUserRequest) -> dict:
    if db.scalar(select(func.count()).select_from(User).where(
            func.lower(User.username) == r.username.lower())) > 0:
        raise ApiException.conflict("Username already taken")
    if _email_exists(db, r.email):
        raise ApiException.conflict("Email already in use")
    role = db.scalar(select(Role).where(Role.name == r.role.value))
    u = User(username=r.username.strip(), email=r.email.strip(), full_name=r.fullName.strip(),
             password_hash=hash_password(r.password), role=role)
    db.add(u)
    db.flush()
    if r.role == RoleName.STUDENT:
        if not r.rollNumber or not r.rollNumber.strip():
            raise ApiException.bad_request("rollNumber is required for students")
        if _roll_exists(db, r.rollNumber):
            raise ApiException.conflict("Roll number already in use")
        db.add(Student(user=u, roll_number=r.rollNumber.strip(), class_name=r.className))
    elif r.role == RoleName.TEACHER:
        db.add(Teacher(user=u, employee_id=r.employeeId, department=r.department))
    db.flush()
    audit.log(db, actor, "USER_CREATED", "User", u.id, f"{u.username} ({r.role.value})")
    db.commit()
    return dto(db, u)


def _assert_not_last_admin(db: Session, u: User) -> None:
    if u.role.name == RoleName.ADMIN.value and u.enabled and count_by_role(db, RoleName.ADMIN) <= 1:
        raise ApiException.bad_request("Cannot remove the last administrator")


def update_user(db: Session, actor: Principal, user_id: int, r: UpdateUserRequest) -> dict:
    u = get_user(db, user_id)
    if u.email.lower() != r.email.lower() and _email_exists(db, r.email):
        raise ApiException.conflict("Email already in use")
    u.email = r.email.strip()
    u.full_name = r.fullName.strip()
    if r.enabled is not None and r.enabled != u.enabled:
        if not r.enabled:
            if u.id == actor.id:
                raise ApiException.bad_request("You cannot disable your own account")
            _assert_not_last_admin(db, u)
        u.enabled = r.enabled
    s = _student_of(db, user_id)
    if s is not None:
        if r.rollNumber and r.rollNumber.strip() and r.rollNumber.lower() != s.roll_number.lower():
            if _roll_exists(db, r.rollNumber):
                raise ApiException.conflict("Roll number already in use")
            s.roll_number = r.rollNumber.strip()
        s.class_name = r.className
    t = _teacher_of(db, user_id)
    if t is not None:
        t.employee_id = r.employeeId
        t.department = r.department
    audit.log(db, actor, "USER_UPDATED", "User", user_id, u.username)
    db.commit()
    return dto(db, u)


def reset_password(db: Session, actor: Principal, user_id: int, r: ResetPasswordRequest) -> None:
    u = get_user(db, user_id)
    u.password_hash = hash_password(r.newPassword)
    audit.log(db, actor, "PASSWORD_RESET", "User", user_id, u.username)
    db.commit()


def delete_user(db: Session, actor: Principal, user_id: int) -> None:
    u = get_user(db, user_id)
    if u.id == actor.id:
        raise ApiException.bad_request("You cannot delete your own account")
    _assert_not_last_admin(db, u)
    username = u.username
    s, t = _student_of(db, user_id), _teacher_of(db, user_id)
    if s is not None:
        db.delete(s)
    if t is not None:
        db.delete(t)
    db.flush()
    db.delete(u)
    db.flush()
    audit.log(db, actor, "USER_DELETED", "User", user_id, username)
    db.commit()


def roles(db: Session) -> List[dict]:
    return [{"id": r.id, "name": r.name, "permissions": sorted(r.permissions)}
            for r in db.scalars(select(Role).order_by(Role.id)).all()]


def update_permissions(db: Session, actor: Principal, role_id: int, r: UpdatePermissionsRequest) -> dict:
    role = db.get(Role, role_id)
    if role is None:
        raise ApiException.not_found("Role")
    if role.name == RoleName.ADMIN.value:
        raise ApiException.bad_request("Administrator permissions cannot be changed")
    if role.name == RoleName.STUDENT.value:
        raise ApiException.bad_request("Students have no assignable permissions")
    for p in r.permissions:
        if p not in Permission.ALL:
            raise ApiException.bad_request(f"Unknown permission: {p}")
    role.set_permissions(r.permissions)
    audit.log(db, actor, "ROLE_PERMISSIONS_UPDATED", "Role", role_id, f"{role.name}: {sorted(r.permissions)}")
    db.commit()
    return {"id": role.id, "name": role.name, "permissions": sorted(role.permissions)}


def _count(db: Session, model) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def stats(db: Session) -> dict:
    finalized = db.scalar(select(func.count()).select_from(Evaluation)
                          .where(Evaluation.status == EvaluationStatus.FINALIZED.value)) or 0
    return {"students": count_by_role(db, RoleName.STUDENT), "teachers": count_by_role(db, RoleName.TEACHER),
            "admins": count_by_role(db, RoleName.ADMIN), "subjects": _count(db, Subject), "exams": _count(db, Exam),
            "submissions": _count(db, Submission), "evaluations": _count(db, Evaluation),
            "finalizedEvaluations": finalized, "auditEvents": _count(db, AuditLog)}


def audit_logs(db: Session, q: Optional[str], page: int, size: int) -> dict:
    size = min(size, 100)
    stmt = select(AuditLog)
    needle = norm(q)
    if needle:
        stmt = stmt.where(contains(AuditLog.username, needle) | contains(AuditLog.action, needle)
                          | contains(AuditLog.entity_type, needle))
    return paginate(db, stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()), page, size,
                    lambda a: {"id": a.id, "username": a.username, "action": a.action,
                               "entityType": a.entity_type, "entityId": a.entity_id, "details": a.details,
                               "ipAddress": a.ip_address, "createdAt": mapper.iso(a.created_at)})


def students(db: Session, q: Optional[str], page: int, size: int) -> dict:
    size = min(size, 100)
    stmt = select(Student).join(User, Student.user_id == User.id)
    needle = norm(q)
    if needle:
        stmt = stmt.where(contains(Student.roll_number, needle) | contains(User.full_name, needle))
    return paginate(db, stmt.order_by(Student.roll_number), page, size, mapper.student)

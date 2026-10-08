import logging

from sqlalchemy import func, select

from .config import settings
from .db import SessionLocal
from .models import Permission, Role, RoleName, Student, Submission, SubmissionStatus, Teacher, User
from .security import hash_password

log = logging.getLogger("inkgrade.seed")


def _create_user(db, username, email, name, password, role_name) -> User:
    role = db.scalar(select(Role).where(Role.name == role_name.value))
    u = User(username=username, email=email, full_name=name, password_hash=hash_password(password), role=role)
    db.add(u)
    db.flush()
    return u


def run() -> None:
    with SessionLocal() as db:
        for n in RoleName:
            r = db.scalar(select(Role).where(Role.name == n.value))
            if r is None:
                r = Role(name=n.value)
                db.add(r)
                db.flush()
                if n == RoleName.TEACHER:
                    r.set_permissions(Permission.ALL)
            if n == RoleName.ADMIN:
                r.set_permissions(Permission.ALL)
        db.flush()
        admin_role = db.scalar(select(Role).where(Role.name == RoleName.ADMIN.value))
        if db.scalar(select(func.count()).select_from(User).where(User.role_id == admin_role.id)) == 0:
            _create_user(db, settings.admin_username, settings.admin_email, "System Administrator",
                         settings.admin_password, RoleName.ADMIN)
            log.info("Created default administrator '%s'", settings.admin_username)
        if settings.seed_demo and db.scalar(
                select(func.count()).select_from(User).where(func.lower(User.username) == "teacher1")) == 0:
            t = _create_user(db, "teacher1", "teacher1@inkgrade.local", "Demo Teacher", "Teacher@123",
                             RoleName.TEACHER)
            db.add(Teacher(user=t, employee_id="T-001", department="Science"))
            for i in (1, 2):
                su = _create_user(db, f"student{i}", f"student{i}@inkgrade.local", f"Demo Student {i}",
                                  "Student@123", RoleName.STUDENT)
                db.add(Student(user=su, roll_number=f"R-00{i}", class_name="10-A"))
            log.info("Seeded demo users: teacher1/Teacher@123, student1..2/Student@123")
        # anything left EVALUATING by a crash/restart can never complete
        for s in db.scalars(select(Submission).where(Submission.status == SubmissionStatus.EVALUATING.value)):
            s.status = SubmissionStatus.FAILED.value
            s.error_message = "Evaluation interrupted by a server restart; please start it again"
        db.commit()

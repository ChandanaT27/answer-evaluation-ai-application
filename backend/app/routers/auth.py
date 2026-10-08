from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import mapper
from ..db import get_db
from ..errors import ApiException
from ..models import Student, Teacher, User
from ..schemas import ChangePasswordRequest, LoginRequest
from ..security import (Principal, client_ip, create_token, current_principal, expires_in_seconds, hash_password,
                        verify_password)
from ..services import audit

router = APIRouter(prefix="/auth")


def user_dto(db: Session, u: User) -> dict:
    s = db.scalar(select(Student).where(Student.user_id == u.id))
    t = db.scalar(select(Teacher).where(Teacher.user_id == u.id))
    return mapper.user(u, s, t)


@router.post("/login")
def login(r: LoginRequest, request: Request, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(func.lower(User.username) == r.username.lower()))
    if u is None or not u.enabled or not verify_password(r.password, u.password_hash):
        audit.log_as(db, None, r.username, "LOGIN_FAILED", "User", None, None, client_ip(request))
        db.commit()
        raise ApiException.unauthorized("Invalid username or password")
    u.last_login_at = datetime.now(timezone.utc)
    audit.log_as(db, u.id, u.username, "LOGIN", "User", u.id, None, client_ip(request))
    db.commit()
    return {"token": create_token(u), "tokenType": "Bearer", "expiresIn": expires_in_seconds(),
            "user": user_dto(db, u)}


@router.get("/me")
def me(p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    return user_dto(db, db.get(User, p.id))


@router.post("/change-password", status_code=204)
def change_password(r: ChangePasswordRequest, p: Principal = Depends(current_principal),
                    db: Session = Depends(get_db)):
    u = db.get(User, p.id)
    if not verify_password(r.currentPassword, u.password_hash):
        raise ApiException.bad_request("Current password is incorrect")
    u.password_hash = hash_password(r.newPassword)
    audit.log(db, p, "PASSWORD_CHANGED", "User", u.id, None)
    db.commit()
    return Response(status_code=204)

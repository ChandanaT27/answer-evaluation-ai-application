from typing import Optional

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Permission, RoleName
from ..schemas import CreateUserRequest, ResetPasswordRequest, UpdatePermissionsRequest, UpdateUserRequest
from ..security import Principal, require_role
from ..services import users

router = APIRouter(prefix="/admin")
Admin = Depends(require_role("ADMIN"))


@router.get("/users")
def list_users(role: Optional[RoleName] = None, q: Optional[str] = None, page: int = 0, size: int = 20,
               _: Principal = Admin, db: Session = Depends(get_db)):
    return users.list_users(db, role, q, page, min(size, 100))


@router.get("/users/{user_id}")
def get_user(user_id: int, _: Principal = Admin, db: Session = Depends(get_db)):
    return users.dto(db, users.get_user(db, user_id))


@router.post("/users", status_code=201)
def create_user(r: CreateUserRequest, p: Principal = Admin, db: Session = Depends(get_db)):
    return users.create_user(db, p, r)


@router.put("/users/{user_id}")
def update_user(user_id: int, r: UpdateUserRequest, p: Principal = Admin, db: Session = Depends(get_db)):
    return users.update_user(db, p, user_id, r)


@router.post("/users/{user_id}/reset-password", status_code=204)
def reset_password(user_id: int, r: ResetPasswordRequest, p: Principal = Admin, db: Session = Depends(get_db)):
    users.reset_password(db, p, user_id, r)
    return Response(status_code=204)


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, p: Principal = Admin, db: Session = Depends(get_db)):
    users.delete_user(db, p, user_id)
    return Response(status_code=204)


@router.get("/roles")
def roles(_: Principal = Admin, db: Session = Depends(get_db)):
    return users.roles(db)


@router.get("/permissions")
def permissions(_: Principal = Admin):
    return sorted(Permission.ALL)


@router.put("/roles/{role_id}/permissions")
def update_permissions(role_id: int, r: UpdatePermissionsRequest, p: Principal = Admin,
                       db: Session = Depends(get_db)):
    return users.update_permissions(db, p, role_id, r)


@router.get("/stats")
def stats(_: Principal = Admin, db: Session = Depends(get_db)):
    return users.stats(db)


@router.get("/audit-logs")
def audit_logs(q: Optional[str] = None, page: int = 0, size: int = 30, _: Principal = Admin,
               db: Session = Depends(get_db)):
    return users.audit_logs(db, q, page, size)

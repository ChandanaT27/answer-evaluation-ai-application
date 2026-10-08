from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional, Set

import bcrypt
import jwt
from fastapi import Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .errors import ApiException
from .models import User

if len(settings.jwt_secret.encode("utf-8")) < 32:
    raise RuntimeError("JWT_SECRET must be at least 32 bytes")


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8")[:72], bcrypt.gensalt()).decode("ascii")


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8")[:72], hashed.encode("ascii"))
    except ValueError:
        return False


def create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user.username, "uid": user.id, "role": user.role.name,
               "iat": int(now.timestamp()),
               "exp": int((now + timedelta(minutes=settings.jwt_expiration_minutes)).timestamp())}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def expires_in_seconds() -> int:
    return settings.jwt_expiration_minutes * 60


def username_from_token(token: str) -> Optional[str]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"],
                          options={"verify_iat": False}).get("sub")
    except jwt.PyJWTError:
        return None


@dataclass
class Principal:
    id: int
    username: str
    role: str
    permissions: Set[str] = field(default_factory=set)
    ip: Optional[str] = None

    @property
    def is_admin(self) -> bool:
        return self.role == "ADMIN"

    @property
    def is_teacher(self) -> bool:
        return self.role == "TEACHER"

    @property
    def is_student(self) -> bool:
        return self.role == "STUDENT"

    def has(self, permission: str) -> bool:
        return permission in self.permissions


def client_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


def current_principal(request: Request, db: Session = Depends(get_db)) -> Principal:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise ApiException.unauthorized()
    username = username_from_token(header[7:])
    if not username:
        raise ApiException.unauthorized()
    user = db.scalar(select(User).where(func.lower(User.username) == username.lower()))
    if user is None or not user.enabled:
        raise ApiException.unauthorized()
    return Principal(user.id, user.username, user.role.name, set(user.role.permissions), client_ip(request))


def require_role(*roles: str) -> Callable:
    def dep(p: Principal = Depends(current_principal)) -> Principal:
        if p.role not in roles:
            raise ApiException.forbidden("You do not have permission to perform this action")
        return p
    return dep


def require_permission(permission: str) -> Callable:
    def dep(p: Principal = Depends(current_principal)) -> Principal:
        if not p.has(permission):
            raise ApiException.forbidden("You do not have permission to perform this action")
        return p
    return dep

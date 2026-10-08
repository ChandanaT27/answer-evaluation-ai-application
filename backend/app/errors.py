import logging
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Dict, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("inkgrade")


class ApiException(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message

    @staticmethod
    def not_found(what: str) -> "ApiException":
        return ApiException(404, f"{what} not found")

    @staticmethod
    def bad_request(msg: str) -> "ApiException":
        return ApiException(400, msg)

    @staticmethod
    def conflict(msg: str) -> "ApiException":
        return ApiException(409, msg)

    @staticmethod
    def forbidden(msg: str) -> "ApiException":
        return ApiException(403, msg)

    @staticmethod
    def unauthorized(msg: str = "Authentication required") -> "ApiException":
        return ApiException(401, msg)


def _body(status: int, message: str, request: Request, fields: Optional[Dict[str, str]] = None) -> JSONResponse:
    try:
        reason = HTTPStatus(status).phrase
    except ValueError:
        reason = "Error"
    return JSONResponse(status_code=status, content={
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status, "error": reason, "message": message,
        "path": request.url.path, "fieldErrors": fields})


def _field_name(loc) -> str:
    parts = [p for p in loc if p != "body"]
    out = ""
    for p in parts:
        out += f"[{p}]" if isinstance(p, int) else (f".{p}" if out else str(p))
    return out


def _message(err: dict) -> str:
    if err.get("type") == "missing":
        return "must not be blank"
    msg = err.get("msg", "invalid value")
    return msg[len("Value error, "):] if msg.startswith("Value error, ") else msg


def register_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiException)
    async def api(request: Request, exc: ApiException):
        return _body(exc.status, exc.message, request)

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        if any(e["loc"] and e["loc"][0] != "body" for e in errors) or \
                any(e.get("type") in ("json_invalid", "model_attributes_type") for e in errors) or \
                (errors and errors[0]["loc"] == ("body",)):
            return _body(400, "Malformed or missing request data", request)
        fields: Dict[str, str] = {}
        for e in errors:
            fields.setdefault(_field_name(e["loc"]), _message(e))
        return _body(400, "Validation failed", request, fields)

    @app.exception_handler(StarletteHTTPException)
    async def http(request: Request, exc: StarletteHTTPException):
        messages = {404: "Resource not found", 405: "Method not allowed"}
        return _body(exc.status_code, messages.get(exc.status_code, str(exc.detail)), request)

    @app.exception_handler(IntegrityError)
    async def integrity(request: Request, exc: IntegrityError):
        log.warning("Data integrity violation: %s", exc.orig)
        return _body(409, "Operation conflicts with existing data (duplicate or in use)", request)

    @app.exception_handler(Exception)
    async def other(request: Request, exc: Exception):
        log.exception("Unhandled error")
        return _body(500, "Unexpected server error", request)

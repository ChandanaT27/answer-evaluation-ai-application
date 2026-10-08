import logging
from pathlib import Path
from typing import Any, Dict

import httpx

from .config import settings
from .errors import ApiException

log = logging.getLogger("inkgrade.ai")


def _client() -> httpx.Client:
    headers = {"X-API-Key": settings.ai_api_key} if settings.ai_api_key.strip() else {}
    return httpx.Client(base_url=settings.ai_base_url, headers=headers,
                        timeout=httpx.Timeout(settings.ai_timeout_seconds, connect=10))


def _call(fn) -> Dict[str, Any]:
    try:
        with _client() as c:
            r = fn(c)
            r.raise_for_status()
            body = r.json()
            if not body:
                raise ApiException(502, "AI service returned an empty response")
            return body
    except httpx.HTTPStatusError as e:
        log.warning("AI service error %s: %s", e.response.status_code, e.response.text)
        raise ApiException(502, f"AI service error: {e.response.status_code} {e.response.text}")
    except httpx.HTTPError as e:
        log.warning("AI service unreachable: %s", e)
        raise ApiException(503, "AI service is unavailable")


def ocr(path: Path, filename: str) -> Dict[str, Any]:
    """Returns {text, confidence, pages, engine}."""
    data = Path(path).read_bytes()
    return _call(lambda c: c.post("/ocr", files={"file": (filename, data)}))


def evaluate(request: Dict[str, Any]) -> Dict[str, Any]:
    """request/response use the AI service's snake_case JSON."""
    return _call(lambda c: c.post("/evaluate", json=request))

import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from .config import settings
from .errors import ApiException

EXT_TYPES = {
    "pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "bmp": "image/bmp", "tif": "image/tiff", "tiff": "image/tiff", "txt": "text/plain",
}


@dataclass
class StoredFile:
    relative_path: str
    original_name: str
    content_type: str


def sanitize(name: Optional[str]) -> str:
    if not name or not name.strip():
        return "upload"
    base = name.replace("\\", "/")
    base = base[base.rfind("/") + 1:]
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", base)
    return base[-120:] if len(base) > 120 else base


def extension(name: str) -> str:
    i = name.rfind(".")
    return "" if i < 0 else name[i + 1:].lower()


def _starts_with(h: bytes, *sig: int) -> bool:
    return len(h) >= len(sig) and all(h[i] == sig[i] for i in range(len(sig)))


def _is_text(h: bytes) -> bool:
    if b"\x00" in h:
        return False
    # a 4096-byte cut may split a multibyte char; tolerate by trimming up to 3 trailing bytes
    for trim in range(0, min(3, len(h)) + 1):
        try:
            h[:len(h) - trim].decode("utf-8")
            return True
        except UnicodeDecodeError:
            continue
    return False


def content_matches(ext: str, h: bytes) -> bool:
    if ext == "pdf":
        return _starts_with(h, 0x25, 0x50, 0x44, 0x46)
    if ext == "png":
        return _starts_with(h, 0x89, 0x50, 0x4E, 0x47)
    if ext in ("jpg", "jpeg"):
        return _starts_with(h, 0xFF, 0xD8, 0xFF)
    if ext == "bmp":
        return _starts_with(h, 0x42, 0x4D)
    if ext in ("tif", "tiff"):
        return _starts_with(h, 0x49, 0x49, 42, 0) or _starts_with(h, 0x4D, 0x4D, 0, 42)
    if ext == "txt":
        return _is_text(h)
    return False


def content_type_for(path: str) -> str:
    return EXT_TYPES.get(extension(path), "application/octet-stream")


class FileStorage:
    """Stores uploads outside the web root under random names after extension + magic-byte validation."""

    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def store(self, upload: Optional[UploadFile], category: str, max_bytes: Optional[int] = None) -> StoredFile:
        limit = max_bytes or settings.max_upload_bytes
        data = upload.file.read(limit + 1) if upload is not None else b""
        if not data:
            raise ApiException.bad_request("Uploaded file is empty")
        if len(data) > limit:
            raise ApiException(413, "Uploaded file is too large")
        original = sanitize(upload.filename)
        ext = extension(original)
        if ext not in EXT_TYPES:
            raise ApiException.bad_request("Unsupported file type. Allowed: " + ", ".join(EXT_TYPES))
        if not content_matches(ext, data[:4096]):
            raise ApiException.bad_request("File content does not match its extension")
        cat = re.sub(r"[^a-z0-9_-]", "", category)
        directory = (self.root / cat).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        name = f"{uuid.uuid4()}.{ext}"
        target = (directory / name).resolve()
        if self.root not in target.parents:
            raise ApiException.bad_request("Invalid storage path")
        target.write_bytes(data)
        return StoredFile(f"{cat}/{name}", original, EXT_TYPES[ext])

    def resolve(self, relative_path: str) -> Path:
        p = (self.root / relative_path).resolve()
        if self.root not in p.parents or not p.is_file():
            raise ApiException.not_found("File")
        return p

    def delete_quietly(self, relative_path: Optional[str]) -> None:
        if not relative_path:
            return
        try:
            p = (self.root / relative_path).resolve()
            if self.root in p.parents:
                p.unlink(missing_ok=True)
        except OSError:
            pass


storage = FileStorage(settings.storage_root)

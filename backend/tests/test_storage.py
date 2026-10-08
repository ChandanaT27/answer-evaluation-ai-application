import pytest
from fastapi import UploadFile
from io import BytesIO

from app.errors import ApiException
from app.storage import FileStorage


def upload(name, data):
    return UploadFile(file=BytesIO(data), filename=name)


def test_stores_valid_png_with_random_name(tmp_path):
    s = FileStorage(str(tmp_path))
    f = s.store(upload("../../evil name.png", b"\x89PNG\x01\x02\x03"), "answer-sheets")
    assert f.relative_path.startswith("answer-sheets/")
    assert ".." not in f.relative_path
    assert "/" not in f.original_name
    assert s.resolve(f.relative_path).exists()


def test_rejects_disallowed_extension_and_spoofed_content(tmp_path):
    s = FileStorage(str(tmp_path))
    with pytest.raises(ApiException):
        s.store(upload("a.exe", b"\x01\x02"), "x")
    with pytest.raises(ApiException):
        s.store(upload("a.png", b"not an image"), "x")
    with pytest.raises(ApiException):
        s.store(upload("a.pdf", b""), "x")


def test_resolve_blocks_path_traversal(tmp_path):
    with pytest.raises(ApiException):
        FileStorage(str(tmp_path)).resolve("../../etc/passwd")

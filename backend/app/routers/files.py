from pathlib import Path
from typing import Optional

from fastapi.responses import FileResponse

from ..storage import content_type_for


def inline(path: Path, name: Optional[str]) -> FileResponse:
    filename = name or path.name
    return FileResponse(path, media_type=content_type_for(path.name), content_disposition_type="inline",
                        filename=filename, headers={"X-Content-Type-Options": "nosniff"})

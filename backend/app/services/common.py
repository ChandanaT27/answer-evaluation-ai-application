from math import ceil
from typing import Any, Callable, Iterable, List

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


def norm(q) -> str:
    return "" if q is None else q.strip()


def contains(column, needle: str):
    """Case-insensitive substring match."""
    return func.lower(column).contains(needle.lower(), autoescape=True)


def page_of(content: List[Any], page: int, size: int, total: int) -> dict:
    return {"content": content, "page": page, "size": size, "totalElements": total,
            "totalPages": ceil(total / size) if size > 0 else 0}


def paginate(db: Session, stmt: Select, page: int, size: int, mapper: Callable[[Any], Any]) -> dict:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.scalars(stmt.offset(page * size).limit(size)).unique().all()
    return page_of([mapper(r) for r in rows], page, size, total)


def in_memory_page(items: Iterable[Any], page: int, size: int, mapper: Callable[[Any], Any]) -> dict:
    """Mirrors the original behaviour for student views: the whole filtered list is returned as one page."""
    items = list(items)
    return page_of([mapper(i) for i in items], page, size, len(items))

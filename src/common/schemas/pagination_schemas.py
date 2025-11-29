from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Metadata for pagination."""

    itemsPerPage: int
    totalItems: int
    currentPage: int
    totalPages: int
    sortBy: list[list[str]] = Field(default_factory=list)
    filter: dict | None = None


class PaginationLinks(BaseModel):
    """Links for navigating paginated results."""

    last: str | None = None
    next: str | None = None
    current: str | None = None


class PaginatedResponse[T](BaseModel):
    """Generic paginated response wrapper."""

    data: list[T]
    meta: PaginationMeta
    links: PaginationLinks

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Metadata for pagination."""

    itemsPerPage: int
    totalItems: int
    currentPage: int
    totalPages: int
    sortBy: list[list[str]] = Field(default_factory=list)


class PaginationLinks(BaseModel):
    """Links for navigating paginated results."""

    last: str | None = None
    next: str | None = None
    current: str | None = None


class Company(BaseModel):
    """Details about a company."""

    id: int
    registrationNumber: str
    name: str
    address: str
    logo: str | None = None


class Tag(BaseModel):
    """Details about a physical NFC/QR tag."""

    id: int
    uid: str
    siteId: int


class CallAnsweredBy(BaseModel):
    """Details of the user who answered a call log."""

    id: int
    gender: str
    uniqueId: str
    dateOfBirth: str
    type: str
    firstName: str
    lastName: str
    role: str
    phoneNumber: str


class SecurityGuard(BaseModel):
    """Details of a security guard user."""

    id: int
    gender: str
    uniqueId: str
    dateOfBirth: str
    type: str
    company: Company | None = None
    firstName: str
    lastName: str
    role: str
    phoneNumber: str


class SiteWithoutTags(BaseModel):
    """A version of Site used in nested objects where tags and owner are suppressed."""

    id: int
    tagId: str
    name: str
    latitude: str
    longitude: str
    phoneNumber: str
    requiredPatrolsPerGuard: int
    notificationsEnabled: bool
    notificationCycle: str
    ownerUserId: int | None = None
    patrolType: str
    securityGuardCount: int
    admin: dict | None = None
    owner: None = None
    company: Company
    tags: None = None


class Patrol(BaseModel):
    """Schema for a single patrol record."""

    id: int
    date: str  # "YYYY-MM-DD"
    startTime: str  # "HH:MM:SS"
    securityGuardUniqueId: str | None = None
    securityGuard: SecurityGuard | None = None
    site: SiteWithoutTags | None = None


class Site(BaseModel):
    """Details about a single monitoring site."""

    id: int
    tagId: str
    name: str
    latitude: str
    longitude: str
    phoneNumber: str
    requiredPatrolsPerGuard: int | None = None
    notificationsEnabled: bool
    notificationCycle: str | None = None
    ownerUserId: int | None = None
    patrolType: str
    securityGuardCount: int
    admin: dict | None = None
    owner: dict | None = None
    company: Company
    tags: list[Tag]
    latestPatrol: Patrol | None = None


class LoginResponse(BaseModel):
    """Schema for the successful login response."""

    access_token: str


class GetStatsResponse(BaseModel):
    """Schema for system-wide statistics."""

    companyCount: int
    companyAdminCount: int
    siteAdminCount: int
    securityGuardCount: int
    siteCount: int
    tagCount: int


class Shift(BaseModel):
    """Schema for a site shift."""

    id: int
    type: Literal["DAY", "NIGHT"]
    site: SiteWithoutTags
    securityGuards: list[SecurityGuard]


class CallLog(BaseModel):
    """Schema for a recorded call log."""

    id: int
    time: str
    date: str
    isAnswered: bool
    response: str | None = None
    site: SiteWithoutTags
    answeredBy: CallAnsweredBy | None = None


class ServerHealthResponse(BaseModel):
    status: Literal["ok", "sick"]


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: PaginationMeta
    links: PaginationLinks

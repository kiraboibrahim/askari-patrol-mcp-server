from typing import Literal, TypeVar

from common.schemas.base_schemas import (
    BaseCompany,
    BasePatrol,
    BaseSecurityGuard,
    BaseSite,
    BaseSiteAdmin,
    BaseSiteOwner,
    BaseTag,
    Company,
)
from common.schemas.pagination_schemas import PaginatedResponse
from pydantic import BaseModel

T = TypeVar("T")


class SecurityGuardInShift(BaseSecurityGuard):
    company: Company


class Shift(BaseModel):
    """Schema for a site shift."""

    id: int
    type: Literal["DAY", "NIGHT"]
    site: BaseSite
    securityGuards: list[SecurityGuardInShift]


class SiteInCallLog(BaseSite):
    """Site details as they appear in call log responses."""

    pass  # No additional fields beyond BaseSite


class SiteInShift(BaseSite):
    """Site details as they appear in shift responses."""

    company: Company
    admin: dict | None = None


class CallLogAnsweredBy(BaseSecurityGuard):
    """Security guard details when they answer a call log."""


class SiteInNotification(BaseSite):
    """Site details as they appear in notification responses."""

    company: Company
    admin: dict | None = None


class Notification(BaseModel):
    """Schema for a site notification/alert."""

    id: int
    dateCreatedAt: str  # "YYYY-MM-DD"
    timeCreatedAt: str  # "HH:MM:SS"
    site: SiteInNotification


class GetGuardListItem(BaseSecurityGuard):
    company: BaseCompany


class CallLog(BaseModel):
    """Schema for a recorded call log."""

    id: int
    time: str  # "HH:MM"
    date: str  # "YYYY-MM-DD"
    isAnswered: bool
    response: str | None = None
    site: SiteInCallLog
    answeredBy: CallLogAnsweredBy | None = None


class SiteListItem(BaseSite):
    """Full site details as shown in GET /sites list."""

    admin: BaseSiteAdmin | None = None
    owner: BaseSiteOwner | None = None
    company: Company
    tags: list[BaseTag]
    latestPatrol: BasePatrol | None = None


class SiteInPatrol(BaseSite):
    """Site details as they appear in patrol responses (minimal fields only)."""

    pass  # Only base fields, no company/admin/tags


class GuardPatrolListItem(BasePatrol):
    site: SiteInPatrol


class SitePatrolListItem(BasePatrol):
    site: SiteInPatrol


GetGuardsResponse = PaginatedResponse[GetGuardListItem]
GetGuardPatrolsResponse = PaginatedResponse[GuardPatrolListItem]

GetSiteNotificationsResponse = PaginatedResponse[Notification]
GetSiteCallLogsResponse = PaginatedResponse[CallLog]
GetSitesRespnose = PaginatedResponse[SiteListItem]
GetSiteShiftsResponse = list[Shift]
GetSiteGuardsResponse = list[SecurityGuardInShift]
GetSitePatrolsResponse = PaginatedResponse[SiteInPatrol]


class LoginResponse(BaseModel):
    """Schema for the successful login response."""

    access_token: str


class GetServerHealthResponse(BaseModel):
    status: Literal["ok", "sick"]


class GetStatsResponse(BaseModel):
    """Schema for system-wide statistics."""

    companyCount: int
    companyAdminCount: int
    siteAdminCount: int
    securityGuardCount: int
    siteCount: int
    tagCount: int


class PerformanceDailyStat(BaseModel):
    """Schema for a guard's daily performance stats."""

    date: str  # "YYYY-MM-DD"
    score: float
    validPatrols: int
    expectedPatrols: int


class PerformanceNotification(BaseModel):
    """Schema for a performance notification (e.g., absent day)."""

    date: str  # "YYYY-MM-DD"
    message: str


class PerformanceMonth(BaseModel):
    """Schema for the month context in performance report."""

    year: int
    month: int


class PerformanceGuard(BaseModel):
    """Minimal guard info as shown in performance reports."""

    id: int
    name: str
    uniqueId: str


class GetGuardPerformanceReportResponse(BaseModel):
    """Schema for the comprehensive guard performance report."""

    securityGuard: PerformanceGuard
    month: PerformanceMonth
    overallMonthScore: str  # e.g., "75.50"
    dailyStats: list[PerformanceDailyStat]
    notifications: list[PerformanceNotification]
    patrols: list[BasePatrol]

from typing import Generic, Literal, TypedDict, TypeVar

# Generic type for items in the data list
T = TypeVar("T")


class PaginationMeta(TypedDict):
    itemsPerPage: int
    totalItems: int
    currentPage: int
    totalPages: int
    sortBy: list[list[str]]


class PaginationLinks(TypedDict):
    first: str | None
    previous: str | None
    current: str | None


class PaginatedResponse(TypedDict, Generic[T]):
    data: list[T]
    meta: PaginationMeta
    links: PaginationLinks


class LoginResponse(TypedDict):
    access_token: str


class StatsResponse(TypedDict):
    companyCount: int
    companyAdminCount: int
    siteAdminCount: int
    securityGuardCount: int
    siteCount: int
    tagCount: int


class Company(TypedDict, total=False):
    id: int
    registrationNumber: str
    name: str
    address: str
    logo: str | None


class Tag(TypedDict):
    id: int
    uid: str
    siteId: int


class Site(TypedDict, total=False):
    id: int
    tagId: str
    name: str
    latitude: str
    longitude: str
    phoneNumber: str
    requiredPatrolsPerGuard: int
    notificationsEnabled: bool
    notificationCycle: str
    ownerUserId: int | None
    patrolType: str
    securityGuardCount: int
    admin: str | None
    owner: str | None
    company: Company
    tags: list[Tag]
    latestPatrol: str | None


class SecurityGuard(TypedDict):
    id: int
    gender: str
    uniqueId: str
    dateOfBirth: str
    type: str
    company: Company
    firstName: str
    lastName: str
    role: str
    phoneNumber: str


class SiteWithoutTags(Site, total=False):
    tags: None
    owner: None
    admin: dict | None


class Shift(TypedDict):
    id: int
    type: Literal["DAY", "NIGHT"]
    site: SiteWithoutTags
    securityGuards: list[SecurityGuard]


class CallAnsweredBy(TypedDict):
    id: int
    gender: str
    uniqueId: str
    dateOfBirth: str
    type: str
    firstName: str
    lastName: str
    role: str
    phoneNumber: str


class CallLog(TypedDict):
    id: int
    time: str
    date: str
    isAnswered: bool
    response: str | None
    site: SiteWithoutTags
    answeredBy: CallAnsweredBy | None


class Patrol(TypedDict):
    id: int
    date: str  # "YYYY-MM-DD"
    startTime: str  # "HH:MM:SS"
    securityGuardUniqueId: str
    securityGuard: SecurityGuard | None
    site: SiteWithoutTags

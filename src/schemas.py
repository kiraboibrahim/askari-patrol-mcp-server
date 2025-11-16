from typing import TypedDict, TypeVar, Generic, List, Optional, Literal

# Generic type for items in the data list
T = TypeVar("T")  

class PaginationMeta(TypedDict):
    itemsPerPage: int
    totalItems: int
    currentPage: int
    totalPages: int
    sortBy: List[List[str]]


class PaginationLinks(TypedDict):
    first: Optional[str]
    previous: Optional[str]
    current: Optional[str]


class PaginatedResponse(TypedDict, Generic[T]):
    data: List[T]
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
    logo: Optional[str]


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
    ownerUserId: Optional[int]
    patrolType: str
    securityGuardCount: int
    admin: Optional[str]
    owner: Optional[str]
    company: Company
    tags: List[Tag]
    latestPatrol: Optional[str]

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
    admin: Optional[dict] 

class Shift(TypedDict):
    id: int
    type: Literal["DAY", "NIGHT"]
    site: SiteWithoutTags
    securityGuards: List[SecurityGuard]


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
    response: Optional[str]
    site: SiteWithoutTags
    answeredBy: Optional[CallAnsweredBy]

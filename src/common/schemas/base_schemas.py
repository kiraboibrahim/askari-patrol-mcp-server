from pydantic import BaseModel


class BaseCompany(BaseModel):
    """Base company fields shared across all company representations."""

    id: int
    registrationNumber: str
    name: str
    address: str
    logo: str | None = None


class Company(BaseCompany):
    """Full company details."""

    theme: dict | None = None


class BaseSite(BaseModel):
    """Base site fields shared across all site representations."""

    id: int
    tagId: str
    name: str
    latitude: str
    longitude: str
    phoneNumber: str
    requiredPatrolsPerGuard: int
    notificationsEnabled: bool
    notificationCycle: str | None
    ownerUserId: int | None = None
    patrolType: str
    securityGuardCount: int


class BaseSecurityGuard(BaseModel):
    """Base security guard fields shared across all guard representations."""

    id: int
    gender: str
    uniqueId: str
    dateOfBirth: str
    type: str
    firstName: str
    lastName: str
    role: str
    phoneNumber: str


class BaseTag(BaseModel):
    """Details about a physical NFC/QR tag."""

    id: int
    uid: str
    siteId: int


class BaseSiteOwner(BaseModel):
    """Site owner details."""

    id: int
    email: str
    firstName: str
    lastName: str
    role: str
    phoneNumber: str


class BaseSiteAdmin(BaseModel):
    """Site admin details with nested site reference."""

    id: int
    companyId: int
    siteId: int
    site: BaseSite  # Nested site with just base fields
    email: str
    firstName: str
    lastName: str
    role: str
    phoneNumber: str


class BasePatrol(BaseModel):
    id: int
    date: str  # "YYYY-MM-DD"
    startTime: str  # "HH:MM:SS"
    securityGuardUniqueId: str | None = None
    securityGuard: BaseSecurityGuard | None = None

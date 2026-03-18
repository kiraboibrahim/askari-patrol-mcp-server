from pydantic import BaseModel


class BaseCompany(BaseModel):
    """Base company fields shared across all company representations."""

    registrationNumber: str
    name: str
    address: str
    logo: str | None = None


class Company(BaseCompany):
    """Full company details."""

    theme: dict | None = None


class BaseSite(BaseModel):
    """Base site fields shared across all site representations."""

    name: str
    latitude: str
    longitude: str
    phoneNumber: str
    requiredPatrolsPerGuard: int | None = None
    notificationsEnabled: bool
    notificationCycle: str | None
    patrolType: str
    securityGuardCount: int


class BaseSecurityGuard(BaseModel):
    """Base security guard fields shared across all guard representations."""

    gender: str
    dateOfBirth: str
    firstName: str
    lastName: str
    phoneNumber: str


class BaseTag(BaseModel):
    """Details about a physical NFC/QR tag."""

    pass


class BaseSiteOwner(BaseModel):
    """Site owner details."""

    email: str
    firstName: str
    lastName: str
    role: str
    phoneNumber: str


class BaseSiteAdmin(BaseModel):
    """Site admin details with nested site reference."""

    site: BaseSite  # Nested site with just base fields
    email: str
    firstName: str
    lastName: str
    role: str
    phoneNumber: str


class BasePatrol(BaseModel):
    date: str  # "YYYY-MM-DD"
    startTime: str  # "HH:MM:SS"
    securityGuard: BaseSecurityGuard | None = None

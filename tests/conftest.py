import pytest
import respx
from askari_patrol_server.api import AskariPatrolAsyncClient
from common.schemas import (
    CallAnsweredBy,
    CallLog,
    Company,
    GetStatsResponse,
    LoginResponse,
    PaginatedResponse,
    PaginationLinks,
    PaginationMeta,
    Patrol,
    SecurityGuard,
    Shift,
    Site,
    SiteWithoutTags,
    Tag,
)

MOCK_TOKEN = "mock_access_token_12345"

MOCK_LOGIN_RESPONSE = LoginResponse(access_token=MOCK_TOKEN).model_dump()

MOCK_STATS_RESPONSE = GetStatsResponse(
    companyCount=1,
    companyAdminCount=2,
    siteAdminCount=3,
    securityGuardCount=50,
    siteCount=10,
    tagCount=100,
).model_dump()

MOCK_COMPANY = Company(
    id=1, name="Acme Inc.", registrationNumber="REG-123", address="101 Main St"
).model_dump()

MOCK_SITE_DATA = Site(
    id=1,
    name="Main Office",
    latitude="0.1",
    longitude="32.1",
    tagId="SITE-TAG-001",
    phoneNumber="12345",
    requiredPatrolsPerGuard=3,
    notificationsEnabled=True,
    notificationCycle="DAILY",
    patrolType="Scheduled",
    securityGuardCount=5,
    company=MOCK_COMPANY,
    tags=[Tag(id=1, uid="TAG-001", siteId=1)],
).model_dump()

MOCK_SITE_WITHOUT_TAGS = SiteWithoutTags(
    id=1,
    name="Main Office",
    latitude="0.1",
    longitude="32.1",
    tagId="SITE-TAG-001",
    phoneNumber="12345",
    requiredPatrolsPerGuard=3,
    notificationsEnabled=True,
    notificationCycle="DAILY",
    patrolType="Scheduled",
    securityGuardCount=5,
    company=MOCK_COMPANY,
    tags=None,
    owner=None,
    admin=None,
).model_dump()

MOCK_PAGINATION_META = PaginationMeta(
    itemsPerPage=10, totalItems=1, currentPage=1, totalPages=1, sortBy=[]
).model_dump()

MOCK_PAGINATION_LINKS = PaginationLinks(
    last="/sites?page=1", next=None, current="/sites?page=1"
).model_dump()

MOCK_PAGINATED_SITE = PaginatedResponse[Site](
    data=[MOCK_SITE_DATA], meta=MOCK_PAGINATION_META, links=MOCK_PAGINATION_LINKS
).model_dump()

MOCK_SECURITY_GUARD = SecurityGuard(
    id=5,
    firstName="John",
    lastName="Doe",
    gender="M",
    uniqueId="SG-001",
    dateOfBirth="1990-01-01",
    type="REGULAR",
    role="Guard",
    phoneNumber="12345",
    company=MOCK_COMPANY,
).model_dump()

MOCK_SHIFTS = [
    Shift(
        id=101,
        type="DAY",
        site=MOCK_SITE_WITHOUT_TAGS,
        securityGuards=[MOCK_SECURITY_GUARD],
    ).model_dump()
]

MOCK_CALL_ANSWERED_BY = CallAnsweredBy(
    id=10,
    firstName="Jane",
    lastName="Smith",
    gender="F",
    uniqueId="SA-001",
    dateOfBirth="1985-05-05",
    type="ADMIN",
    role="SiteAdmin",
    phoneNumber="54321",
).model_dump()

MOCK_PAGINATED_CALL_LOG = PaginatedResponse[CallLog](
    data=[
        CallLog(
            id=1,
            time="10:00:00",
            date="2023-01-01",
            isAnswered=True,
            response="Fire drill completed",
            site=MOCK_SITE_WITHOUT_TAGS,
            answeredBy=MOCK_CALL_ANSWERED_BY,
        ).model_dump()
    ],
    meta=MOCK_PAGINATION_META,
    links=MOCK_PAGINATION_LINKS,
).model_dump()

MOCK_PAGINATED_PATROL = PaginatedResponse[Patrol](
    data=[
        Patrol(
            id=1,
            date="2023-01-01",
            startTime="08:00:00",
            securityGuardUniqueId="SG-001",
            securityGuard=MOCK_SECURITY_GUARD,
            site=MOCK_SITE_WITHOUT_TAGS,
        ).model_dump()
    ],
    meta=MOCK_PAGINATION_META,
    links=MOCK_PAGINATION_LINKS,
).model_dump()

MOCK_PAGINATED_GUARDS = PaginatedResponse[SecurityGuard](
    data=[MOCK_SECURITY_GUARD], meta=MOCK_PAGINATION_META, links=MOCK_PAGINATION_LINKS
).model_dump()


@pytest.fixture(autouse=True)
def mock_respx():
    with respx.mock:
        yield


@pytest.fixture
def client():
    """Provides an instance of the client for each test."""
    return AskariPatrolAsyncClient()


@pytest.fixture
def mock_token():
    """Provides the mock access token."""
    return MOCK_TOKEN


@pytest.fixture
def mock_login_response():
    """Provides the mock login response payload."""
    return MOCK_LOGIN_RESPONSE


@pytest.fixture
def mock_stats_response():
    """Provides the mock stats response payload."""
    return MOCK_STATS_RESPONSE


@pytest.fixture
def mock_paginated_site():
    """Provides the mock paginated site response payload."""
    return MOCK_PAGINATED_SITE


@pytest.fixture
def mock_shifts():
    """Provides the mock shifts list payload."""
    return MOCK_SHIFTS


@pytest.fixture
def mock_paginated_call_log():
    """Provides the mock paginated call log response payload."""
    return MOCK_PAGINATED_CALL_LOG


@pytest.fixture
def mock_paginated_patrol():
    """Provides the mock paginated patrol response payload."""
    return MOCK_PAGINATED_PATROL


@pytest.fixture
def mock_paginated_guards():
    """Provides the mock paginated security guards response payload."""
    return MOCK_PAGINATED_GUARDS

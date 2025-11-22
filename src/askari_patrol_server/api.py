import httpx
from common.schemas import (
    CallLog,
    LoginResponse,
    PaginatedResponse,
    Patrol,
    SecurityGuard,
    Shift,
    Site,
    StatsResponse,
)


class AskariPatrolAsyncClient(httpx.AsyncClient):
    """Async HTTP client for Askari Patrol API."""

    _BASE_URL = "https://guardtour.legitsystemsug.com"

    def __init__(self):
        super().__init__(base_url=self._BASE_URL, timeout=30.0)
        self._token: str | None = None

    def _set_auth_header(self, token: str):
        self._token = token
        self.headers.update({"Authorization": f"Bearer {token}"})

    async def login(self, *, username: str, password: str) -> LoginResponse:
        resp = await self.post(
            "/auth/signin",
            json={"username": username, "password": password},
        )
        resp.raise_for_status()
        data = resp.json()
        self._set_auth_header(data["access_token"])
        return data

    async def get_stats(self) -> StatsResponse:
        resp = await self.get("/stats")
        resp.raise_for_status()
        return resp.json()

    async def get_sites(self, page: int | None = 1) -> PaginatedResponse[Site]:
        resp = await self.get("/sites", params={"page": page})
        resp.raise_for_status()
        return resp.json()

    async def get_site_shifts(self, site_id: int) -> list[Shift]:
        resp = await self.get(f"/sites/{site_id}/shifts")
        resp.raise_for_status()
        return resp.json()

    async def get_site_call_logs(
        self, site_id: int, page: int | None = 1
    ) -> PaginatedResponse[CallLog]:
        resp = await self.get(f"/sites/{site_id}/call-logs", params={"page": page})
        resp.raise_for_status()
        return resp.json()

    async def get_site_patrols(
        self, site_id: int, page: int | None = 1
    ) -> PaginatedResponse[Patrol]:
        # No auth required - use fresh client without auth headers
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self._BASE_URL}/sites/{site_id}/patrols",
                params={"page": page},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_site_monthly_score(self, site_id: int, year: int, month: int) -> str:
        resp = await self.get(f"/sites/{site_id}/{year}/{month}/performance")
        resp.raise_for_status()
        return resp.text

    async def get_site_notifications(
        self, site_id: int, page: int | None = 1
    ) -> PaginatedResponse[dict]:
        resp = await self.get(f"/sites/{site_id}/notifications", params={"page": page})
        resp.raise_for_status()
        return resp.json()

    async def search_guards(
        self, query: str, page: int | None = 1
    ) -> PaginatedResponse[SecurityGuard]:
        resp = await self.get(
            "/users/security-guards", params={"search": query, "page": page}
        )
        resp.raise_for_status()
        return resp.json()

    async def get_guard_patrols(
        self, guard_id: int, page: int | None = 1
    ) -> PaginatedResponse[Patrol]:
        # No auth required - use fresh client without auth headers
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self._BASE_URL}/users/security-guards/{guard_id}/patrols",
                params={"page": page},
            )
            resp.raise_for_status()
            return resp.json()

"""
Askari Patrol API Client Module.

This module provides an asynchronous HTTP client for interacting with the
Askari Patrol guard tour management system API. It handles authentication,
site management, patrol tracking, and notification retrieval.
"""

import httpx
from common.schemas.response_schemas import (
    GetGuardPatrolsResponse,
    GetGuardsResponse,
    GetSiteCallLogsResponse,
    GetSiteGuardsResponse,
    GetSiteNotificationsResponse,
    GetSitePatrolsResponse,
    GetSiteShiftsResponse,
    GetSitesRespnose,
    GetStatsResponse,
    LoginResponse,
)
from common.utils import is_token_valid


class AskariPatrolAsyncClient(httpx.AsyncClient):
    """
    Async HTTP client for the Askari Patrol API.

    Inherits from httpx.AsyncClient to provide specialized methods for
    interacting with the Askari Patrol backend services.
    """

    _BASE_URL = "https://guardtour.legitsystemsug.com"

    def __init__(self):
        """Initialize the client with base URL and default timeout."""
        super().__init__(base_url=self._BASE_URL, timeout=30.0)
        self._token: str | None = None

    def _set_auth_header(self, token: str):
        """
        Update client headers with the provided JWT bearer token.

        Args:
            token: The access token string.
        """
        self._token = token
        self.headers.update({"Authorization": f"Bearer {token}"})

    async def login(self, username: str, password: str) -> LoginResponse:
        """
        Authenticate with the API and store the access token.

        Args:
            username: User's login name.
            password: User's password.

        Returns:
            LoginResponse: A dict containing the access_token.
        """
        resp = await self.post(
            "/auth/signin",
            json={"username": username, "password": password},
        )
        resp.raise_for_status()
        data = resp.json()
        self._set_auth_header(data["access_token"])
        return data

    async def get_stats(self) -> GetStatsResponse:
        """
        Retrieve system-wide statistics.

        Returns:
            GetStatsResponse: Counts for sites, guards, companies, etc.
        """
        resp = await self.get("/stats")
        resp.raise_for_status()
        return resp.json()

    async def search_sites(self, query: str, page: int | None = 1) -> GetSitesRespnose:
        """
        Search for sites using a query string.

        Args:
            query: The search term for site names or descriptions.
            page: Optional page number for pagination.

        Returns:
            GetSitesRespnose: Paginated list of matching sites.
        """
        resp = await self.get("/sites", params={"search": query, "page": page})
        resp.raise_for_status()
        return resp.json()

    async def get_sites(self, page: int | None = 1) -> GetSitesRespnose:
        """
        List all sites with pagination.

        Args:
            page: Optional page number for pagination.

        Returns:
            GetSitesRespnose: Paginated list of all sites.
        """
        resp = await self.get("/sites", params={"page": page})
        resp.raise_for_status()
        return resp.json()

    async def get_site_shifts(self, site_id: int) -> GetSiteShiftsResponse:
        """
        List all shifts configured for a specific site.

        Args:
            site_id: Database ID of the site.

        Returns:
            GetSiteShiftsResponse: List of shift objects.
        """
        resp = await self.get(f"/sites/{site_id}/shifts")
        resp.raise_for_status()
        return resp.json()

    async def get_site_guards(self, site_id: int) -> GetSiteGuardsResponse:
        """
        Retrieve all security guards assigned to a site across all shifts.

        Args:
            site_id: Database ID of the site.

        Returns:
            GetSiteGuardsResponse: Aggregated list of guards from all site shifts.
        """
        site_shifts = await self.get_site_shifts(site_id)
        guards = []
        for shift in site_shifts:
            guards.extend(shift["securityGuards"])
        return guards

    async def get_site_call_logs(
        self, site_id: int, page: int | None = 1
    ) -> GetSiteCallLogsResponse:
        """
        Retrieve paginated call logs for a specific site.

        Args:
            site_id: Database ID of the site.
            page: Optional page number for pagination.

        Returns:
            GetSiteCallLogsResponse: List of recorded calls for the site.
        """
        resp = await self.get(f"/sites/{site_id}/call-logs", params={"page": page})
        resp.raise_for_status()
        return resp.json()

    async def get_site_patrols(
        self,
        site_id: int,
        page: int | None = 1,
        start_date: str | None = None,
        end_date: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> GetSitePatrolsResponse:
        """
        Retrieve paginated patrol records for a specific site with optional filters.

        Filters are mapped to the NestJS pagination syntax (e.g., $btw, $gte, $lte).

        Args:
            site_id: Database ID of the site.
            page: Optional page number for pagination.
            start_date: Start date for filtering (YYYY-MM-DD).
            end_date: End date for filtering (YYYY-MM-DD).
            start_time: Start time for filtering (HH:MM).
            end_time: End time for filtering (HH:MM).

        Returns:
            GetSitePatrolsResponse: Paginated list of patrols.
        """
        params = {"page": page}

        # Build date filters
        if start_date and end_date:
            params["filter.date"] = f"$btw:{start_date},{end_date}"
        elif start_date:
            params["filter.date"] = f"$gte:{start_date}"
        elif end_date:
            params["filter.date"] = f"$lte:{end_date}"

        # Build time filters
        if start_time and end_time:
            params["filter.startTime"] = f"$btw:{start_time},{end_time}"
        elif start_time:
            params["filter.startTime"] = f"$gte:{start_time}"
        elif end_time:
            params["filter.startTime"] = f"$lte:{end_time}"

        # Use a fresh client to bypass authenticated session for public patrol endpoints
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self._BASE_URL}/sites/{site_id}/patrols",
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_site_monthly_score(self, site_id: int, year: int, month: int) -> str:
        """
        Get the site's performance score for a specific month.

        Args:
            site_id: Database ID of the site.
            year: Year as integer (e.g., 2024).
            month: Month as integer (1-12).

        Returns:
            str: Raw score text from the API.
        """
        resp = await self.get(f"/sites/{site_id}/{year}/{month}/performance")
        resp.raise_for_status()
        return resp.text

    async def get_site_notifications(
        self,
        site_id: int,
        page: int | None = 1,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> GetSiteNotificationsResponse:
        """
        Retrieve paginated notifications/alerts for a specific site.

        Args:
            site_id: Database ID of the site.
            page: Optional page number for pagination.
            start_date: Start date for filtering (YYYY-MM-DD).
            end_date: End date for filtering (YYYY-MM-DD).

        Returns:
            GetSiteNotificationsResponse: List of alerts for the site.
        """
        params = {"page": page}

        # Map date filters to API-expected field 'dateCreatedAt'
        if start_date and end_date:
            params["filter.dateCreatedAt"] = f"$btw:{start_date},{end_date}"
        elif start_date:
            params["filter.dateCreatedAt"] = f"$gte:{start_date}"
        elif end_date:
            params["filter.dateCreatedAt"] = f"$lte:{end_date}"

        resp = await self.get(f"/sites/{site_id}/notifications", params=params)
        resp.raise_for_status()
        return resp.json()

    async def search_guards(
        self, query: str, page: int | None = 1
    ) -> GetGuardsResponse:
        """
        Search for security guards across the system.

        Args:
            query: Search string for guard names or UIDs.
            page: Optional page number for pagination.

        Returns:
            GetGuardsResponse: Paginated results for security guards.
        """
        resp = await self.get(
            "/users/security-guards", params={"search": query, "page": page}
        )
        resp.raise_for_status()
        return resp.json()

    async def get_guard_patrols(
        self,
        guard_id: int,
        page: int | None = 1,
        start_date: str | None = None,
        end_date: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> GetGuardPatrolsResponse:
        """
        Retrieve patrol records for a specific security guard with optional filters.

        Args:
            guard_id: Database ID of the security guard.
            page: Optional page number for pagination.
            start_date: Start date for filtering (YYYY-MM-DD).
            end_date: End date for filtering (YYYY-MM-DD).
            start_time: Start time for filtering (HH:MM).
            end_time: End time for filtering (HH:MM).

        Returns:
            GetGuardPatrolsResponse: Paginated list of patrols by this guard.
        """
        params = {"page": page}

        # Apply date range logic
        if start_date and end_date:
            params["filter.date"] = f"$btw:{start_date},{end_date}"
        elif start_date:
            params["filter.date"] = f"$gte:{start_date}"
        elif end_date:
            params["filter.date"] = f"$lte:{end_date}"

        # Apply time range logic
        if start_time and end_time:
            params["filter.startTime"] = f"$btw:{start_time},{end_time}"
        elif start_time:
            params["filter.startTime"] = f"$gte:{start_time}"
        elif end_time:
            params["filter.startTime"] = f"$lte:{end_time}"

        # Fresh client to avoid bearer headers on public endpoints
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self._BASE_URL}/users/security-guards/{guard_id}/patrols",
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    def is_authenticated(self) -> bool:
        """
        Check if the current client session has a valid, non-expired token.

        Returns:
            bool: True if authenticated, False otherwise.
        """
        return self._token is not None and is_token_valid(self._token)

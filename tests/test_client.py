import httpx
import pytest
import respx
from askari_patrol_server.api import AskariPatrolAsyncClient


class TestAskariPatrolAsyncClient:
    BASE_URL = AskariPatrolAsyncClient._BASE_URL

    @pytest.mark.asyncio
    async def test_login_success_and_auth_set(
        self, client: AskariPatrolAsyncClient, mock_login_response, mock_token
    ):
        """Tests successful login and verification that the auth header is set."""

        route = respx.post(f"{self.BASE_URL}/auth/signin").mock(
            return_value=httpx.Response(200, json=mock_login_response)
        )

        response = await client.login(username="test", password="password")

        assert route.called
        assert response.get("access_token") == mock_token
        # Check if the internal state of the client was updated
        assert client._token == mock_token
        assert client.headers.get("Authorization") == f"Bearer {mock_token}"

    @pytest.mark.asyncio
    async def test_login_failure_raises_exception(
        self, client: AskariPatrolAsyncClient
    ):
        """Tests that a non-2xx response during login raises an HTTPStatusError."""

        respx.post(f"{self.BASE_URL}/auth/signin").mock(
            return_value=httpx.Response(401, json={"detail": "Unauthorized"})
        )

        with pytest.raises(httpx.HTTPStatusError):
            await client.login(username="bad", password="creds")

    @pytest.mark.asyncio
    async def test_get_stats(
        self, client: AskariPatrolAsyncClient, mock_token, mock_stats_response
    ):
        """Tests successful retrieval of statistics using new field names."""

        client._set_auth_header(mock_token)

        route = respx.get(f"{self.BASE_URL}/stats").mock(
            return_value=httpx.Response(200, json=mock_stats_response)
        )

        response = await client.get_stats()

        assert route.called
        # Assert against the new schema fields
        assert response.get("siteCount") == 10
        assert response.get("securityGuardCount") == 50
        assert client.headers.get("Authorization") == f"Bearer {mock_token}"

    @pytest.mark.asyncio
    async def test_search_sites_with_query_and_page(
        self, client: AskariPatrolAsyncClient, mock_token, mock_paginated_site
    ):
        """Tests the search_sites method, checking the new paginated structure."""

        client._set_auth_header(mock_token)

        route = respx.get(
            f"{self.BASE_URL}/sites", params={"search": "Office", "page": 2}
        ).mock(return_value=httpx.Response(200, json=mock_paginated_site))

        response = await client.search_sites("Office", page=2)

        assert route.called
        # Check new structure: data, meta, and accessing nested name
        assert response.get("meta").get("currentPage") == 1
        assert response.get("data")[0].get("name") == "Main Office"

    @pytest.mark.asyncio
    async def test_get_sites_default_page(
        self, client: AskariPatrolAsyncClient, mock_token, mock_paginated_site
    ):
        """Tests the get_sites method using the default page parameter."""

        client._set_auth_header(mock_token)

        route = respx.get(f"{self.BASE_URL}/sites", params={"page": 1}).mock(
            return_value=httpx.Response(200, json=mock_paginated_site)
        )

        await client.get_sites()

        assert route.called
        assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_get_site_shifts(
        self, client: AskariPatrolAsyncClient, mock_token, mock_shifts
    ):
        """Tests retrieving a list of shifts for a specific site."""

        client._set_auth_header(mock_token)
        SITE_ID = 42
        route = respx.get(f"{self.BASE_URL}/sites/{SITE_ID}/shifts").mock(
            return_value=httpx.Response(200, json=mock_shifts)
        )

        response = await client.get_site_shifts(SITE_ID)

        assert route.called
        assert isinstance(response, list)
        assert len(response) == 1
        # Check a nested field from the Shift schema
        assert response[0].get("type") == "DAY"
        assert response[0].get("site").get("name") == "Main Office"

    @pytest.mark.asyncio
    async def test_get_site_call_logs(
        self, client: AskariPatrolAsyncClient, mock_token, mock_paginated_call_log
    ):
        """Tests retrieving paginated call logs for a site, checking new field names."""

        client._set_auth_header(mock_token)
        SITE_ID = 42
        route = respx.get(f"{self.BASE_URL}/sites/{SITE_ID}/call-logs").mock(
            return_value=httpx.Response(200, json=mock_paginated_call_log)
        )

        response = await client.get_site_call_logs(SITE_ID, page=1)

        assert route.called
        # Check new structure and fields (meta and response)
        assert response.get("meta").get("totalItems") == 1
        assert response.get("data")[0].get("response") == "Fire drill completed"

    @pytest.mark.asyncio
    async def test_get_site_patrols_no_auth(
        self, client: AskariPatrolAsyncClient, mock_paginated_patrol
    ):
        """Tests get_site_patrols, which uses a fresh, unauthenticated client."""

        SITE_ID = 42
        expected_url = f"{self.BASE_URL}/sites/{SITE_ID}/patrols"
        route = respx.get(expected_url, params={"page": 1}).mock(
            return_value=httpx.Response(200, json=mock_paginated_patrol)
        )

        response = await client.get_site_patrols(SITE_ID, page=1)

        assert route.called
        # Check new structure and fields (date, startTime)
        assert response.get("data")[0].get("date") == "2023-01-01"
        assert response.get("data")[0].get("securityGuardUniqueId") == "SG-001"

    @pytest.mark.asyncio
    async def test_get_site_monthly_score(
        self, client: AskariPatrolAsyncClient, mock_token
    ):
        """Tests retrieving a raw text monthly performance score."""

        client._set_auth_header(mock_token)
        SITE_ID = 42
        YEAR = 2023
        MONTH = 10
        MOCK_SCORE = "95.5%"

        route = respx.get(
            f"{self.BASE_URL}/sites/{SITE_ID}/{YEAR}/{MONTH}/performance"
        ).mock(return_value=httpx.Response(200, content=MOCK_SCORE))

        response = await client.get_site_monthly_score(SITE_ID, YEAR, MONTH)

        assert route.called
        assert response == MOCK_SCORE
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_search_guards(
        self, client: AskariPatrolAsyncClient, mock_token, mock_paginated_guards
    ):
        """Tests searching for security guards, checking new field names."""

        client._set_auth_header(mock_token)

        route = respx.get(
            f"{self.BASE_URL}/users/security-guards",
            params={"search": "John", "page": 1},
        ).mock(return_value=httpx.Response(200, json=mock_paginated_guards))

        response = await client.search_guards("John")

        assert route.called
        # Check new structure and fields (firstName)
        assert response.get("data")[0].get("firstName") == "John"
        assert response.get("data")[0].get("company").get("name") == "Acme Inc."

    @pytest.mark.asyncio
    async def test_get_guard_patrols_no_auth(
        self, client: AskariPatrolAsyncClient, mock_paginated_patrol
    ):
        """Tests get_guard_patrols, which uses a fresh, unauthenticated client."""

        GUARD_ID = 10
        expected_url = f"{self.BASE_URL}/users/security-guards/{GUARD_ID}/patrols"
        route = respx.get(expected_url, params={"page": 1}).mock(
            return_value=httpx.Response(200, json=mock_paginated_patrol)
        )

        response = await client.get_guard_patrols(GUARD_ID, page=1)

        assert route.called
        # Check new structure and fields
        assert response.get("data")[0].get("site").get("name") == "Main Office"
        assert response.get("data")[0].get("securityGuardUniqueId") == "SG-001"

    @pytest.mark.asyncio
    async def test_http_error_on_non_2xx_response(
        self, client: AskariPatrolAsyncClient, mock_token
    ):
        """Tests that any method raises an exception on a non-2xx status code."""

        client._set_auth_header(mock_token)
        # Mock a 404 response for the stats endpoint
        respx.get(f"{self.BASE_URL}/stats").mock(return_value=httpx.Response(404))

        with pytest.raises(httpx.HTTPStatusError):
            await client.get_stats()

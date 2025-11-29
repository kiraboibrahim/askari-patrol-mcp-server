from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from common.rollbar_config import initialize_rollbar
from common.schemas.response_schemas import (
    GetGuardPatrolsResponse,
    GetGuardsResponse,
    GetServerHealthResponse,
    GetSiteCallLogsResponse,
    GetSiteGuardsResponse,
    GetSiteNotificationsResponse,
    GetSitePatrolsResponse,
    GetSiteShiftsResponse,
    GetSitesRespnose,
    GetStatsResponse,
    LoginResponse,
)
from mcp.server.fastmcp import FastMCP

from .api import AskariPatrolAsyncClient
from .decorators.track_errors import track_errors


@dataclass
class AppContext:
    client: AskariPatrolAsyncClient


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage API client lifecycle."""
    yield {}


is_rollbar_initialzed = initialize_rollbar()

mcp = FastMCP(
    "Askari Patrol",
    instructions="MCP server for Askari Patrol guard tour management system. "
    "Provides tools to manage sites, security guards, patrols, shifts, and call logs.",
    host="0.0.0.0",
    port=9000,
    lifespan=app_lifespan,
)


def get_client() -> AskariPatrolAsyncClient:
    ctx = mcp.get_context().request_context
    session = ctx.session  # unique per chat user

    if not hasattr(session, "_client"):
        session._client = AskariPatrolAsyncClient()
        session._exit_stack.push_async_callback(session._client.aclose)

    return session._client


@mcp.tool()
@track_errors()
async def login(username: str, password: str) -> LoginResponse:
    """
    Authenticate with the Askari Patrol API.
    Returns an access token that will be used for subsequent requests.
    """
    client = get_client()
    result = await client.login(username, password)
    return {
        "success": True,
        "message": "Login successful",
        "access_token": result["access_token"],
    }


@mcp.tool()
@track_errors()
async def get_stats() -> GetStatsResponse:
    """
    Get overall statistics including counts of companies, admins, guards, sites, and tags.
    Requires authentication.
    """
    client = get_client()
    return await client.get_stats()


@mcp.tool()
@track_errors()
async def search_sites(query: str, page: int = 1) -> GetSitesRespnose:
    """
    Search for sites by name or other criteria.
    Requires authentication.

    Args:
        query: Search query string
        page: Page number for pagination (default: 1)
    """
    client = get_client()
    return await client.search_sites(query, page)


@mcp.tool()
@track_errors()
async def get_sites(page: int = 1) -> GetSitesRespnose:
    """
    Get a paginated list of all sites.
    Requires authentication.

    Args:
        page: Page number for pagination (default: 1)
    """
    client = get_client()
    return await client.get_sites(page)


@mcp.tool()
@track_errors()
async def get_site_shifts(site_id: int) -> GetSiteShiftsResponse:
    """
    Get all shifts for a specific site.
    Requires authentication.

    Args:
        site_id: The ID of the site
    """
    client = get_client()
    return await client.get_site_shifts(site_id)


@mcp.tool()
@track_errors()
async def get_site_guards(site_id: int) -> GetSiteGuardsResponse:
    """
    Get all guards for a specific site.
    Requires authentication.

    Args:
        site_id: The ID of the site
    """
    client = get_client()
    return await client.get_site_guards(site_id)


@mcp.tool()
@track_errors()
async def get_site_patrols(site_id: int, page: int = 1) -> GetSitePatrolsResponse:
    """
    Get paginated patrol records for a specific site.
    Does NOT require authentication.

    Args:
        site_id: The ID of the site
        page: Page number for pagination (default: 1)
    """
    client = get_client()
    return await client.get_site_patrols(site_id, page)


@mcp.tool()
@track_errors()
async def get_site_call_logs(site_id: int, page: int = 1) -> GetSiteCallLogsResponse:
    """
    Get paginated call logs for a specific site.
    Requires authentication.

    Args:
        site_id: The ID of the site
        page: Page number for pagination (default: 1)
    """
    client = get_client()
    return await client.get_site_call_logs(site_id, page)


@mcp.tool()
@track_errors()
async def get_site_notifications(
    site_id: int, page: int = 1
) -> GetSiteNotificationsResponse:
    """
    Get paginated notifications for a specific site.
    Requires authentication.

    Args:
        site_id: The ID of the site
        page: Page number for pagination (default: 1)
    """
    client = get_client()
    return await client.get_site_notifications(site_id, page)


@mcp.tool()
@track_errors()
async def get_site_monthly_score(site_id: int, year: int, month: int) -> str:
    """
    Get the monthly performance score for a specific site.
    Requires authentication.

    Args:
        site_id: The ID of the site
        year: The year (e.g., 2024)
        month: The month (1-12)
    """
    client = get_client()
    return await client.get_site_monthly_score(site_id, year, month)


@mcp.tool()
@track_errors()
async def search_guards(query: str, page: int = 1) -> GetGuardsResponse:
    """
    Search for security guards by name or other criteria.
    Requires authentication.

    Args:
        query: Search query string
        page: Page number for pagination (default: 1)
    """
    client = get_client()
    return await client.search_guards(query, page)


@mcp.tool()
@track_errors()
async def get_guard_patrols(guard_id: int, page: int = 1) -> GetGuardPatrolsResponse:
    """
    Get paginated patrol records for a specific security guard.
    Does NOT require authentication.

    Args:
        guard_id: The ID of the security guard
        page: Page number for pagination (default: 1)
    """
    client = get_client()
    return await client.get_guard_patrols(guard_id, page)


@mcp.tool()
@track_errors()
async def logout() -> dict:
    """
    Logout and clear the client session.
    """
    ctx = mcp.get_context().request_context
    session = ctx.session

    client: AskariPatrolAsyncClient | None = getattr(session, "_client", None)
    if client:
        await client.aclose()
        delattr(session, "_client")

    return {"success": True, "message": "Logged out successfully"}


@mcp.tool()
@track_errors()
async def is_authenticated() -> bool:
    """
    Check if the current session is authenticated.
    """
    ctx = mcp.get_context().request_context
    session = ctx.session

    client: AskariPatrolAsyncClient | None = getattr(session, "_client", None)
    if client:
        return client.is_authenticated()
    return False


@mcp.tool()
@track_errors()
async def is_healthy() -> GetServerHealthResponse:
    """
    Health check endpoint to verify server is running.
    """
    return {
        "status": "ok",
    }


app = mcp.streamable_http_app()

if __name__ == "__main__":
    mcp.run(transport="streamable-http")

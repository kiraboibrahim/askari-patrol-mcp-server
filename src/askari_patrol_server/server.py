"""
Askari Patrol MCP Server.

This module exposes the Askari Patrol guard tour management API as a set of
FastMCP tools consumable by any MCP-compatible AI client (e.g. Claude, Pydantic AI).

Each registered tool is scoped to the HTTP session that issued the request.
``get_client()`` lazily creates a per-session :class:`AskariPatrolAsyncClient`
instance so that every concurrent WhatsApp user gets their own authenticated
connection without sharing state between sessions.

Authentication flow:
    1. An authenticated client calls ``login`` (or the Python client silently
       calls ``restore_session``) to attach a bearer token to the session client.
    2. Subsequent tool calls read that token from the session-local client via
       ``get_client()``, which is sufficient for the entire lifetime of the
       connection.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from common.rollbar_config import initialize_rollbar
from common.schemas.response_schemas import (
    GetGuardPatrolsResponse,
    GetGuardPerformanceReportResponse,
    GetGuardsResponse,
    GetSiteCallLogsResponse,
    GetSiteGuardsResponse,
    GetSiteNotificationsResponse,
    GetSitePatrolsResponse,
    GetSitesResponse,
    LoginResponse,
)
from mcp.server.fastmcp import FastMCP

from .api import AskariPatrolAsyncClient
from .decorators.track_errors import track_errors


@dataclass
class AppContext:
    """Holds application-level state passed through the MCP lifespan."""

    client: AskariPatrolAsyncClient


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage API client lifecycle for the application."""
    yield {}


is_rollbar_initialzed = initialize_rollbar()

mcp = FastMCP(
    "Askari Patrol",
    instructions="MCP server for Askari Patrol guard tour management system. "
    "Provides tools to manage sites, security guards, patrols, shifts, and call logs.",
    host="0.0.0.0",
    port=8000,
    lifespan=app_lifespan,
)


def get_client() -> AskariPatrolAsyncClient:
    """
    Return the session-local API client, creating it on first access.

    Each MCP session (i.e. one WhatsApp user / one chat connection) receives
    its own isolated :class:`AskariPatrolAsyncClient` stored on the session
    object.  This ensures that bearer tokens issued by ``login`` are never
    leaked across sessions.

    The client's lifecycle is tied to the session via ``push_async_callback``,
    so it is properly closed when the session ends.

    Returns:
        AskariPatrolAsyncClient: The caller's session-scoped HTTP client.
    """
    ctx = mcp.get_context().request_context
    session = ctx.session  # unique per chat connection

    if not hasattr(session, "_client"):
        session._client = AskariPatrolAsyncClient()
        # Ensure the client is gracefully closed at end of session
        session._exit_stack.push_async_callback(session._client.aclose)

    return session._client


# ---------------------------------------------------------------------------
# Authentication tools  (login, restore_session, is_authenticated)
#
# These are registered on the MCP server so the Python client can call them
# directly via ``direct_call_tool``.  They are hidden from the LLM's tool
# list by the ``MCPServerStreamableHTTP.filtered()`` call in ``AskariAgent.connect``,
# so the model will never see or attempt to invoke them autonomously.
# ---------------------------------------------------------------------------


@mcp.tool()
@track_errors()
async def login(username: str, password: str) -> LoginResponse:
    """
    Authenticate with the Askari Patrol API.

    Calls the backend ``/auth/signin`` endpoint and stores the resulting JWT
    on the session-local client.  The token is returned to the caller so the
    Python client can persist it to the conversation database for session
    restoration after reconnects.

    Args:
        username: The user's registered email address or username.
        password: The user's plaintext password (transmitted over TLS only).

    Returns:
        LoginResponse: A dict containing ``success``, ``message``, and
            ``access_token`` fields.
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
async def restore_session(token: str) -> dict:
    """
    Restore an authenticated session from a previously obtained JWT.

    Validates the token's expiry before applying it.  Called by the Python
    client (``AskariAgent._restore_session``) automatically on reconnection,
    bypassing the LLM entirely.

    Args:
        token: A JWT bearer token retrieved from the local conversation database.

    Returns:
        dict: ``{"success": True}`` on success or ``{"success": False}`` if the
            token is expired or structurally invalid.
    """
    from common.utils import is_token_valid  # local import avoids circular dep

    client = get_client()
    if not is_token_valid(token):
        return {"success": False, "message": "Token is expired or invalid"}

    client._set_auth_header(token)
    return {"success": True, "message": "Session restored"}


# get_stats is intentionally disabled — it is restricted to super-admin roles
# that are not served by this MCP interface.
#
# @mcp.tool()
# @track_errors()
# async def get_stats() -> GetStatsResponse:
#     """Get overall statistics including site, guard, and company counts."""
#     client = get_client()
#     return await client.get_stats()


# ---------------------------------------------------------------------------
# Site tools
# ---------------------------------------------------------------------------


@mcp.tool()
@track_errors()
async def get_sites(query: str | None = None, page: int = 1) -> GetSitesResponse:
    """
    List or search for sites with pagination.
    Use this to get all sites or search for specific ones by name.
    Requires authentication.

    Args:
        query: Optional search term to filter sites by name. Example: "Gate", "West".
        page: Page number for paginated results. Defaults to 1.

    Returns:
        GetSitesResponse: Paginated list of sites matching the criteria.

    Examples:
        get_sites(query="Gate", page=1)
        get_sites()
    """
    client = get_client()
    return await client.get_sites(query=query, page=page)


@mcp.tool()
@track_errors()
async def is_authenticated() -> dict:
    """
    Check whether the current session has a valid, non-expired token.

    Called by the Python client before every user request as a pre-flight
    authentication gate.  Returns a plain dict so the result can be parsed
    from the MCP ``ToolResult`` content blocks.

    Returns:
        dict: ``{"authenticated": True/False}``
    """
    client = get_client()
    return {"authenticated": client.is_authenticated()}


@mcp.tool()
@track_errors()
async def get_site_guards(site_name: str) -> GetSiteGuardsResponse:
    """
    Retrieve all security guards assigned to a site across all its shifts.
    Requires authentication.

    Args:
        site_name: The exact name of the site. Example: "Riverside"

    Returns:
        GetSiteGuardsResponse: List of guards across all shifts at the site.

    Raises:
        LookupError: If the site name is not found or is ambiguous.

    Examples:
        get_site_guards("Riverside")
        get_site_guards("West Gate")
    """
    client = get_client()
    site_id = await client.resolve_site_id(site_name)
    return await client.get_site_guards(site_id)


@mcp.tool()
@track_errors()
async def get_site_patrols(
    site_name: str,
    page: int = 1,
    start_date: str | None = None,
    end_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> GetSitePatrolsResponse:
    """
    Retrieve patrol records for a specific site with optional date/time filters.
    Requires authentication.

    Args:
        site_name: The exact name of the site. Example: "Riverside"
        page: Page number for paginated results. Defaults to 1.
        start_date: Start of date range filter (YYYY-MM-DD). Example: "2024-01-01"
        end_date: End of date range filter (YYYY-MM-DD). Example: "2024-01-31"
        start_time: Start of time range filter (HH:MM). Example: "08:00"
        end_time: End of time range filter (HH:MM). Example: "18:00"

    Returns:
        GetSitePatrolsResponse: Paginated list of patrol records.

    Raises:
        LookupError: If the site name is not found or is ambiguous.

    Examples:
        get_site_patrols("Riverside", start_date="2024-01-01", end_date="2024-01-31")
        get_site_patrols("West Gate", start_time="08:00", end_time="18:00")
    """
    client = get_client()
    site_id = await client.resolve_site_id(site_name)
    return await client.get_site_patrols(
        site_id,
        page=page,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
    )


@mcp.tool()
@track_errors()
async def get_site_call_logs(site_name: str, page: int = 1) -> GetSiteCallLogsResponse:
    """
    Retrieve call logs for a specific site.
    Requires authentication.

    Args:
        site_name: The exact name of the site. Example: "Riverside"
        page: Page number for paginated results. Defaults to 1.

    Returns:
        GetSiteCallLogsResponse: Paginated list of call logs for the site.

    Raises:
        LookupError: If the site name is not found or is ambiguous.

    Examples:
        get_site_call_logs("Riverside")
        get_site_call_logs("West Gate", page=2)
    """
    client = get_client()
    site_id = await client.resolve_site_id(site_name)
    return await client.get_site_call_logs(site_id, page)


@mcp.tool()
@track_errors()
async def get_site_monthly_score(site_name: str, year: int, month: int) -> str:
    """
    Get the monthly performance score for a specific site.
    Requires authentication.

    Args:
        site_name: The exact name of the site. Example: "Riverside"
        year: The year (e.g., 2024)
        month: The month (1-12)

    Raises:
        LookupError: If the site name is not found or is ambiguous.
    """
    client = get_client()
    site_id = await client.resolve_site_id(site_name)
    return await client.get_site_monthly_score(site_id, year, month)


@mcp.tool()
@track_errors()
async def get_site_notifications(
    site_name: str,
    page: int = 1,
    start_date: str | None = None,
    end_date: str | None = None,
) -> GetSiteNotificationsResponse:
    """
    Retrieve notifications/alerts for a specific site with optional date filters.
    Requires authentication.

    Args:
        site_name: The exact name of the site. Example: "West Gate"
        page: Page number for paginated results. Defaults to 1.
        start_date: Start of date range filter (YYYY-MM-DD). Example: "2024-01-01"
        end_date: End of date range filter (YYYY-MM-DD). Example: "2024-01-31"

    Returns:
        GetSiteNotificationsResponse: Paginated list of site alerts/notifications.

    Raises:
        LookupError: If the site name is not found or is ambiguous.

    Examples:
        get_site_notifications("West Gate", start_date="2024-01-01", end_date="2024-01-31")
    """
    client = get_client()
    site_id = await client.resolve_site_id(site_name)
    return await client.get_site_notifications(
        site_id,
        page=page,
        start_date=start_date,
        end_date=end_date,
    )


# ---------------------------------------------------------------------------
# Guard tools
# ---------------------------------------------------------------------------


@mcp.tool()
@track_errors()
async def search_guards(query: str, page: int = 1) -> GetGuardsResponse:
    """
    Search for security guards by name or uniqueId.
    Use this to find correct guard names for other tools.
    Requires authentication.

    Args:
        query: Full or partial guard name or uniqueId. Example: "John", "GRD-001"
        page: Page number for paginated results. Defaults to 1.

    Returns:
        GetGuardsResponse: Paginated list of guards matching the query.

    Examples:
        search_guards("John")
        search_guards("GRD-001")
    """
    client = get_client()
    return await client.search_guards(query, page)


@mcp.tool()
@track_errors()
async def get_guard_patrols(
    guard_name: str,
    page: int = 1,
    start_date: str | None = None,
    end_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> GetGuardPatrolsResponse:
    """
    Retrieve patrol records for a specific security guard with optional filters.
    Requires authentication.

    Args:
        guard_name: Full name of the guard. Example: "John Doe"
        page: Page number for paginated results. Defaults to 1.
        start_date: Start of date range filter (YYYY-MM-DD). Example: "2024-01-01"
        end_date: End of date range filter (YYYY-MM-DD). Example: "2024-01-31"
        start_time: Start of time range filter (HH:MM). Example: "08:00"
        end_time: End of time range filter (HH:MM). Example: "17:00"

    Returns:
        GetGuardPatrolsResponse: Paginated list of patrols completed by this guard.

    Raises:
        LookupError: If the guard name is not found or is ambiguous.

    Examples:
        get_guard_patrols("John Doe", start_date="2024-01-01", end_date="2024-01-31")
        get_guard_patrols("Jane Smith", start_time="08:00", end_time="17:00")
    """
    client = get_client()
    guard_id = await client.resolve_guard_id(guard_name)
    return await client.get_guard_patrols(
        guard_id,
        page=page,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
    )


@mcp.tool()
@track_errors()
async def get_guard_performance_report(
    guard_name: str, year: int, month: int
) -> GetGuardPerformanceReportResponse:
    """
    Get the monthly performance report for a specific security guard.
    Requires authentication.

    Args:
        guard_name: Full name of the guard. Example: "John Doe"
        year: The year (e.g., 2024)
        month: The month as a number (1-12). Example: 3 for March

    Returns:
        GetGuardPerformanceReportResponse: Detailed monthly performance metrics.

    Raises:
        LookupError: If the guard name is not found or is ambiguous.

    Examples:
        get_guard_performance_report("John Doe", 2024, 3)
    """
    client = get_client()
    guard_id = await client.resolve_guard_id(guard_name)
    return await client.get_guard_performance_report(guard_id, year, month)


if __name__ == "__main__":
    try:
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        print("👋 Program stopped by user. Goodbye!")

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount

from .api import AskariPatrolAsyncClient

mcp = FastMCP(name="Askari Patrol MCP Server")


@dataclass
class AppContext:
    client: AskariPatrolAsyncClient


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage API client lifecycle."""
    async with AskariPatrolAsyncClient() as client:
        yield AppContext(client=client)


mcp = FastMCP(
    "Askari Patrol",
    instructions="MCP server for Askari Patrol guard tour management system. "
    "Provides tools to manage sites, security guards, patrols, shifts, and call logs.",
    lifespan=app_lifespan,
)


def get_client() -> AppContext:
    ctx = mcp.get_context().request_context.lifespan_context
    return ctx.client


@mcp.tool()
async def login(username: str, password: str) -> dict:
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
async def get_stats() -> dict:
    """
    Get overall statistics including counts of companies, admins, guards, sites, and tags.
    Requires authentication.
    """
    client = get_client()
    return await client.get_stats()


@mcp.tool()
async def get_sites(page: int = 1) -> dict:
    """
    Get a paginated list of all sites.
    Requires authentication.

    Args:
        page: Page number for pagination (default: 1)
    """
    client = get_client()
    return await client.get_sites(page)


@mcp.tool()
async def get_site_shifts(site_id: int) -> list:
    """
    Get all shifts for a specific site.
    Requires authentication.

    Args:
        site_id: The ID of the site
    """
    client = get_client()
    return await client.get_site_shifts(site_id)


@mcp.tool()
async def get_site_patrols(site_id: int, page: int = 1) -> dict:
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
async def get_site_call_logs(site_id: int, page: int = 1) -> dict:
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
async def get_site_notifications(site_id: int, page: int = 1) -> dict:
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
async def search_guards(query: str, page: int = 1) -> dict:
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
async def get_guard_patrols(guard_id: int, page: int = 1) -> dict:
    """
    Get paginated patrol records for a specific security guard.
    Does NOT require authentication.

    Args:
        guard_id: The ID of the security guard
        page: Page number for pagination (default: 1)
    """
    client = get_client()
    return await client.get_guard_patrols(guard_id, page)


app = Starlette(routes=[Mount("/mcp", app=mcp.streamable_http_app())])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "askari_patrol_server.server:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True,
    )

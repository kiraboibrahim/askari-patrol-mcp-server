"""
Error tracking decorator for FastMCP tools.

This module provides the :func:`track_errors` decorator, which wraps MCP tool
functions to automatically capture and report exceptions to Rollbar.  It works
transparently with both synchronous and asynchronous tools.

Usage::

    @mcp.tool()
    @track_errors()
    async def my_tool(param: str) -> dict:
        ...

    @mcp.tool()
    @track_errors(tool_name="custom_name", log_params=False)
    async def my_async_tool() -> dict:
        ...
"""

import asyncio
import functools
import logging
import os
from collections.abc import Callable

import rollbar

logger = logging.getLogger(__name__)

# Read at import time so the check is O(1) inside each wrapper invocation.
ROLLBAR_SERVER_TOKEN = os.environ.get("ROLLBAR_SERVER_TOKEN")


def track_errors(tool_name: str = None, log_params: bool = True):
    """
    Decorator that reports unhandled tool exceptions to Rollbar.

    Attaches metadata (tool name, error type, and sanitised parameters) to
    each Rollbar report.  If ``ROLLBAR_SERVER_TOKEN`` is not configured the
    error is logged locally instead and re-raised so FastMCP can return a
    structured error response to the caller.

    Args:
        tool_name: Human-readable label for Rollbar reports.
            Defaults to the decorated function's ``__name__``.
        log_params: Whether to include sanitised call parameters in the
            Rollbar payload.  Disable for tools that receive sensitive inputs
            beyond passwords (which are always redacted).

    Returns:
        Callable: The decorated function, preserving its original signature
            via :func:`functools.wraps`.
    """

    def decorator(func: Callable) -> Callable:
        name = tool_name or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                params = _extract_params(args, kwargs, log_params)

                if ROLLBAR_SERVER_TOKEN:
                    rollbar.report_exc_info(
                        extra_data={
                            "tool_name": name,
                            "error_type": type(e).__name__,
                            "params": params,
                        }
                    )
                    logger.info("Reported error in '%s' to Rollbar.", name)
                else:
                    logger.error("'%s' raised an unhandled error: %s", name, e)

                # Re-raise so FastMCP can translate the exception into a
                # structured MCP error response for the client.
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                params = _extract_params(args, kwargs, log_params)

                if ROLLBAR_SERVER_TOKEN:
                    rollbar.report_exc_info(
                        extra_data={
                            "tool_name": name,
                            "error_type": type(e).__name__,
                            "params": params,
                        }
                    )
                    logger.info("Reported error in '%s' to Rollbar.", name)
                else:
                    logger.error("'%s' raised an unhandled error: %s", name, e)

                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def _extract_params(args: tuple, kwargs: dict, log_params: bool) -> dict:
    """
    Build a sanitised parameter dict suitable for Rollbar payloads.

    Passwords and MCP context objects are unconditionally excluded.  All
    remaining values are coerced to strings and truncated at 200 characters
    to keep Rollbar payloads small.

    Args:
        args: Positional arguments passed to the wrapped function.
        kwargs: Keyword arguments passed to the wrapped function.
        log_params: When ``False``, returns early with a placeholder dict
            instead of processing any parameters.

    Returns:
        dict: A mapping of parameter names to sanitised string values.
    """
    if not log_params:
        return {"params_logging": "disabled"}

    params = {}
    for key, value in kwargs.items():
        # Skip MCP context objects and any password-like parameters
        if key == "ctx" or key.lower().startswith("password"):
            continue
        str_value = str(value)
        # Truncate long values to keep the Rollbar payload manageable
        params[key] = str_value[:200] if len(str_value) > 200 else str_value

    return params

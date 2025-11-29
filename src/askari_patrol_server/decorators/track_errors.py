import functools
import logging
import os
from collections.abc import Callable

import rollbar

logger = logging.getLogger(__name__)
ROLLBAR_SERVER_TOKEN = os.environ.get("ROLLBAR_SERVER_TOKEN")


def track_errors(tool_name: str = None, log_params: bool = True):
    """
    Decorator to automatically track tool errors in Rollbar.

    Args:
        tool_name: Name of the tool (defaults to function name)
        log_params: Whether to log function parameters to Rollbar
        include_result: Whether to log successful results (for debugging)

    Usage:
        @mcp.tool()
        @track_errors()
        def my_tool(param: str) -> dict:
            ...

        @mcp.tool()
        @track_errors(tool_name="custom_name", log_params=False)
        async def my_async_tool() -> dict:
            ...
    """

    def decorator(func: Callable) -> Callable:
        # Use function name if tool_name not provided
        name = tool_name or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                return result

            except Exception as e:
                # Extract parameters for logging
                params = _extract_params(args, kwargs, log_params)

                # Report to Rollbar
                if ROLLBAR_SERVER_TOKEN:
                    rollbar.report_exc_info(
                        extra_data={
                            "tool_name": name,
                            "error_type": type(e).__name__,
                            "params": params,
                        }
                    )
                    logger.info(f"Reported error in {name} to Rollbar")
                else:
                    logger.error(f"{name} error: {e}")

                # Re-raise to let FastMCP handle
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                params = _extract_params(args, kwargs, log_params)

                # Report to Rollbar
                if ROLLBAR_SERVER_TOKEN:
                    rollbar.report_exc_info(
                        extra_data={
                            "tool_name": name,
                            "error_type": type(e).__name__,
                            "params": params,
                        }
                    )
                    logger.info(f"Reported error in {name} to Rollbar")
                else:
                    logger.error(f"{name} error: {e}")

                # Re-raise to let FastMCP handle
                raise

        # Return appropriate wrapper based on function type(async vs sync)
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def _extract_params(args: tuple, kwargs: dict, log_params: bool) -> dict:
    """Extract function parameters for logging."""
    if not log_params:
        return {"params_logging": "disabled"}

    # Filter out Context and sensitive data
    params = {}

    # Add non-Context kwargs
    for key, value in kwargs.items():
        if key != "ctx" and not key.lower().startswith("password"):
            # Truncate long values
            str_value = str(value)
            params[key] = str_value[:200] if len(str_value) > 200 else str_value

    return params

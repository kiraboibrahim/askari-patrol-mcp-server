import asyncio
import logging
import os
from typing import Any

import rollbar

logger = logging.getLogger(__name__)

ROLLBAR_SERVER_TOKEN = os.getenv("ROLLBAR_SERVER_TOKEN")


def initialize_rollbar():
    """Initialize Rollbar globally, safe to call multiple times."""
    if not ROLLBAR_SERVER_TOKEN:
        logger.warning("Rollbar not initialized: ROLLBAR_SERVER_TOKEN not set")
        return False

    rollbar.init(
        access_token=ROLLBAR_SERVER_TOKEN,
        code_version=os.getenv("CODE_VERSION", "1.0.0"),
        enabled=True,
        environment=os.getenv("ENVIRONMENT", "development"),
    )

    logger.info("Rollbar initialized")
    return True


async def report_error_to_rollbar_async(
    exc: Exception = None,
    level: str = "error",
    extra_data: dict[str, Any] = None,
    payload_data: dict[str, Any] = None,
):
    """
    Report an exception to Rollbar asynchronously.

    Parameters:
        exc: Optional exception object. If None, uses the current exception in context.
        level: Rollbar level ("error", "warning", "info", "critical")
        extra_data: Dict of additional metadata
        payload_data: Dict to pass directly to Rollbar payload
    """

    def _report():
        if exc:
            rollbar.report_exc_info(
                (type(exc), exc, exc.__traceback__),
                extra_data=extra_data,
                payload_data=payload_data,
                level=level,
            )
        else:
            rollbar.report_exc_info(
                extra_data=extra_data, payload_data=payload_data, level=level
            )

    try:
        if ROLLBAR_SERVER_TOKEN:
            await asyncio.to_thread(_report)
    except Exception as e:
        print(f"Rollbar reporting failed: {e}")

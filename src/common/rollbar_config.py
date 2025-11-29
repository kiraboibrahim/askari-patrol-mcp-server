import asyncio
import logging
import os

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


async def report_error_to_rollbar_async():
    """Report the current exception to Rollbar without blocking the event loop."""
    try:
        if ROLLBAR_SERVER_TOKEN:
            # Run Rollbar's sync call in a background thread
            await asyncio.to_thread(rollbar.report_exc_info)
    except Exception as e:
        print(f"Rollbar reporting failed: {e}")

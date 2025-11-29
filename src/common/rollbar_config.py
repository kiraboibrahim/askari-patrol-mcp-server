# core/rollbar_config.py
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

"""
Common utility functions for the Askari Patrol server.

This module provides shared helpers used by both the MCP server and the
async API client, primarily for JWT validation and payload inspection.
"""

import logging
from typing import Any

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

logger = logging.getLogger(__name__)


def is_token_valid(
    token: str, secret_key: str | None = None, algorithms: list[str] | None = None
) -> bool:
    """
    Validate a JWT by checking its signature and expiration claim.

    When ``secret_key`` is provided the token signature is fully verified.
    When it is ``None`` only the ``exp`` claim is checked — useful for
    client-side expiry detection where the signing secret is unavailable.

    Args:
        token: The encoded JWT string to validate.
        secret_key: Optional HMAC secret used to verify the signature.
            Defaults to ``None`` (expiry-only check).
        algorithms: Acceptable signing algorithms.  Defaults to ``["HS256"]``.

    Returns:
        bool: ``True`` if the token is structurally valid and has not expired,
            ``False`` otherwise.
    """
    if algorithms is None:
        algorithms = ["HS256"]

    try:
        if secret_key:
            jwt.decode(
                token,
                key=secret_key,
                algorithms=algorithms,
                options={"verify_signature": True, "verify_exp": True},
            )
        else:
            # No secret available — verify expiry only (safe for client-side checks).
            jwt.decode(token, options={"verify_signature": False, "verify_exp": True})

        return True

    except ExpiredSignatureError:
        logger.debug("Token rejected: expired.")
        return False

    except InvalidTokenError as e:
        logger.debug("Token rejected: invalid structure or signature. %s", e)
        return False

    except Exception:
        logger.exception("Unexpected error during token validation.")
        return False


def decode_token_payload(token: str) -> dict[str, Any] | None:
    """
    Decode a JWT and return its payload without any verification.

    This function deliberately skips signature and expiry checks, making it
    safe to call on already-expired tokens when you only need to inspect
    claims (e.g. to display a username or company name after session expiry).

    Args:
        token: The encoded JWT string to decode.

    Returns:
        dict[str, Any] | None: The decoded payload dictionary, or ``None``
            if the token is malformed and cannot be decoded at all.

    Warning:
        Do **not** use this function to make access-control decisions.
        Use :func:`is_token_valid` for that purpose.
    """
    try:
        return jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_aud": False,
            },
        )
    except Exception:
        logger.exception("Failed to decode token payload.")
        return None

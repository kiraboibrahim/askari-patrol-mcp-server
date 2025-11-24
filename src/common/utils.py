import os
from typing import Any

import httpx
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError


def is_token_valid(
    token: str, secret_key: str | None = None, algorithms: list[str] | None = None
) -> bool:
    """
    Validates a JWT by checking its signature and expiration time.

    Args:
        token (str): The JWT string to validate.
        secret_key (str, optional): The secret key used to sign the token.
                                    Required for signature verification.
        algorithms (List[str]): A list of acceptable signature algorithms. Defaults to ["HS256"].

    Returns:
        bool: True if the token is valid and not expired, False otherwise.
    """
    if algorithms is None:
        algorithms = ["HS256"]
    try:
        if secret_key:
            jwt.decode(
                token,
                key=secret_key,
                algorithms=algorithms,
                # Explicitly check expiry (exp claim)
                options={"verify_signature": True, "verify_exp": True},
            )
        else:
            # Verify only expiry if no secret key is provided
            jwt.decode(token, options={"verify_signature": False, "verify_exp": True})

        return True

    except ExpiredSignatureError:
        # The token is structurally valid but past its expiration time (exp claim).
        print("Token validation failed: Signature expired.")
        return False

    except InvalidTokenError as e:
        # Catches all other validation failures (e.g., incorrect signature, malformed token).
        print(
            f"Token validation failed: Invalid token structure or signature. Error: {e}"
        )
        return False
    except Exception as e:
        # Catch unexpected errors during decoding.
        print(f"An unexpected error occurred during token decoding: {e}")
        return False


def decode_token_payload(token: str) -> dict[str, Any] | None:
    """
    Decodes a JWT to extract its payload without verifying the signature or expiry.
    Useful for inspecting claims quickly.
    """
    try:
        # Uses 'verify=False' to skip all verification steps, allowing inspection
        # of expired or unsigned tokens.
        return jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_aud": False,
            },
        )
    except Exception as e:
        print(f"Failed to decode token payload: {e}")
        return None


def send_typing_indicator(
    message_id: str,
    channel: str = "whatsapp",
    account_sid: str | None = None,
    auth_token: str | None = None,
) -> dict[Any, Any]:
    """
    Send a typing indicator via Twilio API.

    Args:
        message_id: The Twilio message SID to show typing for
        channel: The messaging channel (default: "whatsapp")
        account_sid: Twilio Account SID (defaults to TWILIO_ACCOUNT_SID env var)
        auth_token: Twilio Auth Token (defaults to TWILIO_AUTH_TOKEN env var)

    Returns:
        Dict containing the API response

    Raises:
        httpx.HTTPStatusError: If the request fails
    """
    account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")

    if not account_sid or not auth_token:
        raise ValueError(
            "Twilio credentials must be provided or set in environment variables"
        )

    data = {"messageId": message_id, "channel": channel}
    response = httpx.post(
        "https://messaging.twilio.com/v2/Indicators/Typing.json",
        auth=(account_sid, auth_token),
        data=data,
    )
    response.raise_for_status()

    return response.json()

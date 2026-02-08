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


def split_whatsapp_message(text: str, limit: int = 1600) -> list[str]:
    """
    Split a message into chunks that fit within the Twilio/WhatsApp character limit.

    Uses a hierarchical splitting strategy to preserve message structure:
    1. Paragraphs (double newlines) - keeps logical sections together
    2. Lines (single newlines) - preserves line breaks
    3. Sentences (. ! ?) - keeps complete thoughts together
    4. Words (spaces) - avoids breaking mid-word
    5. Characters (fallback) - hard split for extremely long words

    Args:
        text: The message text to split
        limit: Maximum characters per chunk (default 1600 for WhatsApp)

    Returns:
        List of message chunks, each ≤ limit characters. Returns empty list
        if text is empty, single-element list if text fits in one chunk.

    Examples:
        >>> split_whatsapp_message("Short message")
        ['Short message']

        >>> split_whatsapp_message("A" * 2000, limit=1600)
        ['AAA...', 'AAA...']  # Split into 2 chunks
    """
    if not text or len(text) <= limit:
        return [text] if text else []

    chunks = []
    current_chunk = ""

    def flush_chunk():
        """Add current chunk to results and reset."""
        nonlocal current_chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = ""

    def add_piece(piece: str):
        """Add piece to current chunk, flushing if needed."""
        nonlocal current_chunk

        # If piece alone exceeds limit, it needs further splitting
        if len(piece) > limit:
            return False

        # If adding piece would exceed limit, flush current chunk first
        if current_chunk and len(current_chunk) + len(piece) > limit:
            flush_chunk()

        current_chunk += piece
        return True

    def split_by_sentences(text: str):
        """Split text by sentence boundaries."""
        import re

        # Split on sentence endings followed by space or newline
        sentences = re.split(r"([.!?]+[\s\n]+)", text)

        # Rejoin punctuation with sentences
        result = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                result.append(sentences[i] + sentences[i + 1])
            else:
                result.append(sentences[i])

        # Add any remaining fragment
        if len(sentences) % 2 == 1:
            result.append(sentences[-1])

        return result

    def split_by_words(text: str):
        """Split text by words, preserving spaces."""
        words = text.split(" ")
        for i, word in enumerate(words):
            word_with_space = word + (" " if i < len(words) - 1 else "")

            if not add_piece(word_with_space):
                # Word is too long, hard split
                split_by_chars(word_with_space)

    def split_by_chars(text: str):
        """Hard split text by character limit."""
        nonlocal current_chunk
        for i in range(0, len(text), limit):
            chunk = text[i : i + limit]
            if current_chunk and len(current_chunk) + len(chunk) > limit:
                flush_chunk()
            current_chunk += chunk

    # Split by paragraphs (double newlines)
    paragraphs = text.split("\n\n")

    for i, para in enumerate(paragraphs):
        # Preserve paragraph separator except after last paragraph
        separator = "\n\n" if i < len(paragraphs) - 1 else ""
        para_with_sep = para + separator

        if add_piece(para_with_sep):
            continue

        # Paragraph too long - split by lines
        lines = para.split("\n")
        for j, line in enumerate(lines):
            line_with_sep = line + ("\n" if j < len(lines) - 1 else "")

            if add_piece(line_with_sep):
                continue

            # Line too long - split by sentences
            sentences = split_by_sentences(line_with_sep)
            for sentence in sentences:
                if add_piece(sentence):
                    continue

                # Sentence too long - split by words
                split_by_words(sentence)

        # Re-add paragraph separator if needed
        if i < len(paragraphs) - 1:
            add_piece("\n\n")

    flush_chunk()
    return chunks

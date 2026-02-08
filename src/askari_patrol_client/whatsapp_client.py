"""
Askari Patrol WhatsApp Bot - FastAPI Server

This module implements a production-ready WhatsApp chatbot powered by the Askari
Patrol Agent. It provides a Twilio webhook endpoint for receiving and responding
to WhatsApp messages, with features including persistent sessions, rate limiting,
concurrent message handling, and health monitoring.

Key Features:
    - Persistent agent sessions per user (maintains conversation context)
    - In-memory rate limiting to prevent abuse
    - Concurrent message detection and queueing
    - WhatsApp typing indicators for better UX
    - Health check endpoint for monitoring
    - Rollbar integration for error tracking
    - MCP server connectivity validation

Architecture:
    - SessionManager: Maintains one long-lived AskariAgent per phone number
    - RateLimiter: Tracks message counts per user within time windows
    - Background Tasks: Async message processing to respond quickly to Twilio
    - Graceful Shutdown: Cleanup of all MCP connections on server stop

Environment Variables:
    Required:
        TWILIO_ACCOUNT_SID: Twilio account identifier
        TWILIO_AUTH_TOKEN: Twilio authentication token
        TWILIO_WHATSAPP_NUMBER: Twilio WhatsApp number (E.164 format)
        GROQ_API_KEY: API key for Groq LLM service

    Optional:
        MCP_SERVER_URL: MCP server endpoint (default: http://localhost:8000/mcp)
        ROLLBAR_SERVER_TOKEN: Rollbar token for error tracking
        RATE_LIMIT_MESSAGES: Max messages per window (default: 10)
        RATE_LIMIT_WINDOW: Rate limit window in seconds (default: 60)

Usage:
    # Development
    python -m askari_patrol_client.server

    # Production (with Gunicorn)
    gunicorn askari_patrol_client.server:create_app --workers 4 --worker-class uvicorn.workers.UvicornWorker

Endpoints:
    POST /webhook: Twilio webhook for incoming WhatsApp messages
    GET /health: Health check endpoint (returns 200 if healthy, 503 otherwise)
    GET /error: Test endpoint for error tracking (raises exception)

See Also:
    - Twilio WhatsApp API: https://www.twilio.com/docs/whatsapp/api
    - FastAPI Background Tasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
"""

import logging
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from common.rollbar_config import initialize_rollbar, report_error_to_rollbar_async
from common.utils import send_typing_indicator, split_whatsapp_message
from fastapi import BackgroundTasks, FastAPI, Form
from fastapi.responses import JSONResponse, PlainTextResponse
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from rollbar.contrib.fastapi import add_to as rollbar_add_to
from twilio.rest import Client

from .agent import AskariAgent
from .prompts import WHATSAPP_SYSTEM_PROMPT

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Environment variable configuration
TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_WHATSAPP_NUMBER = os.environ["TWILIO_WHATSAPP_NUMBER"]
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8000/mcp")
ROLLBAR_SERVER_TOKEN = os.environ.get("ROLLBAR_SERVER_TOKEN")

# Rate limiting configuration
RATE_LIMIT_MESSAGES = int(os.environ.get("RATE_LIMIT_MESSAGES", "10"))
RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", "60"))

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# User-facing messages
MSG_MEDIA_NOT_SUPPORTED = (
    "⚠️ Sorry, I can only process text messages. Please send your request as text."
)
MSG_RATE_LIMITED = "⚠️ You've reached the message limit. Please wait {} seconds before sending more messages."
MSG_PROCESSING_PREVIOUS = "⏳ Please wait, I'm still processing your previous message."
MSG_PROCESSING_ERROR = "I encountered an error processing your message."


class RateLimiter:
    """
    In-memory rate limiter with sliding window implementation.

    Tracks message timestamps per phone number and enforces configurable
    rate limits to prevent abuse and manage API costs.

    The sliding window approach ensures fair rate limiting by only counting
    messages within the current time window, automatically expiring old entries.

    Attributes:
        max_messages (int): Maximum messages allowed per window
        window_seconds (int): Time window duration in seconds
        message_timestamps (dict): Mapping of phone numbers to timestamp lists

    Example:
        >>> limiter = RateLimiter(max_messages=5, window_seconds=60)
        >>> limiter.is_rate_limited("+1234567890")  # First message
        False
        >>> # After 5 messages in 60 seconds...
        >>> limiter.is_rate_limited("+1234567890")
        True
        >>> limiter.get_remaining_time("+1234567890")
        45  # seconds until reset
    """

    def __init__(self, max_messages: int, window_seconds: int):
        """
        Initialize the rate limiter.

        Args:
            max_messages: Maximum number of messages allowed per window
            window_seconds: Duration of the rate limit window in seconds
        """
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.message_timestamps: dict[str, list[float]] = defaultdict(list)

    def is_rate_limited(self, phone_number: str) -> bool:
        """
        Check if a phone number has exceeded the rate limit.

        Automatically cleans up expired timestamps and adds the current
        timestamp if the limit hasn't been reached.

        Args:
            phone_number: The phone number to check (E.164 format)

        Returns:
            bool: True if rate limited, False otherwise

        Side Effects:
            - Removes timestamps outside the current window
            - Adds current timestamp if not rate limited

        Example:
            >>> limiter.is_rate_limited("+1234567890")
            False  # First call adds timestamp
            >>> limiter.is_rate_limited("+1234567890")
            False  # Second call adds timestamp
        """
        now = time.time()
        timestamps = self.message_timestamps[phone_number]

        # Clean up expired timestamps
        cutoff = now - self.window_seconds
        timestamps[:] = [ts for ts in timestamps if ts > cutoff]

        # Check if limit exceeded
        if len(timestamps) >= self.max_messages:
            return True

        # Add current timestamp and allow message
        timestamps.append(now)
        return False

    def get_remaining_time(self, phone_number: str) -> int:
        """
        Calculate seconds until the rate limit resets for a phone number.

        Args:
            phone_number: The phone number to check (E.164 format)

        Returns:
            int: Seconds until the oldest message expires (0 if not limited)

        Example:
            >>> limiter.get_remaining_time("+1234567890")
            42  # 42 seconds until oldest message expires
        """
        if phone_number not in self.message_timestamps:
            return 0

        timestamps = self.message_timestamps[phone_number]
        if not timestamps:
            return 0

        oldest = min(timestamps)
        elapsed = time.time() - oldest
        remaining = max(0, self.window_seconds - elapsed)
        return int(remaining)


class SessionManager:
    """
    Manages persistent AskariAgent sessions for each user.

    Maintains one long-lived agent instance per phone number, enabling
    conversation continuity and reducing connection overhead. Also tracks
    which users are currently being processed to prevent concurrent message
    handling issues.

    Attributes:
        mcp_server_url (str): MCP server endpoint URL
        instructions (str): System prompt for agent initialization
        sessions (dict): Mapping of phone numbers to AskariAgent instances
        processing (set): Phone numbers currently being processed

    Example:
        >>> manager = SessionManager("http://localhost:8000/mcp", "You are...")
        >>> agent = await manager.get_or_create_session("+1234567890")
        >>> # Agent persists for future calls from this number
        >>> same_agent = await manager.get_or_create_session("+1234567890")
        >>> assert agent is same_agent
    """

    def __init__(self, mcp_server_url: str, instructions: str):
        """
        Initialize the session manager.

        Args:
            mcp_server_url: URL of the MCP server to connect to
            instructions: System prompt/instructions for agent behavior
        """
        self.mcp_server_url = mcp_server_url
        self.instructions = instructions
        self.sessions: dict[str, AskariAgent] = {}
        self.processing: set[str] = set()

    async def get_or_create_session(self, phone_number: str) -> AskariAgent:
        """
        Retrieve existing agent session or create a new one.

        Creates a new AskariAgent instance on first contact, then reuses
        it for all subsequent messages from the same phone number. The agent
        maintains conversation history and MCP connections across calls.

        Args:
            phone_number: User's phone number (E.164 format)

        Returns:
            AskariAgent: Connected agent instance ready for use

        Side Effects:
            - Creates and connects new agent if not exists
            - Logs session creation

        Example:
            >>> agent = await manager.get_or_create_session("+1234567890")
            >>> response = await agent.run("Hello")
        """
        if phone_number not in self.sessions:
            logger.info(f"Creating new agent session for {phone_number}")
            agent = AskariAgent(
                server_url=self.mcp_server_url,
                instructions=self.instructions,
                phone_number=phone_number,
            )
            await agent.connect()
            self.sessions[phone_number] = agent

        return self.sessions[phone_number]

    def is_processing(self, phone_number: str) -> bool:
        """
        Check if a message is currently being processed for a user.

        Used to prevent concurrent message handling which could lead to
        race conditions or duplicate responses.

        Args:
            phone_number: User's phone number to check

        Returns:
            bool: True if currently processing, False otherwise

        Example:
            >>> manager.is_processing("+1234567890")
            False
            >>> manager.start_processing("+1234567890")
            >>> manager.is_processing("+1234567890")
            True
        """
        return phone_number in self.processing

    def start_processing(self, phone_number: str) -> None:
        """
        Mark that message processing has started for a user.

        Args:
            phone_number: User's phone number

        Side Effects:
            Adds phone number to the processing set
        """
        self.processing.add(phone_number)

    def finish_processing(self, phone_number: str) -> None:
        """
        Mark that message processing has finished for a user.

        Args:
            phone_number: User's phone number

        Side Effects:
            Removes phone number from the processing set

        Note:
            Uses discard() instead of remove() to avoid KeyError if
            the phone number wasn't in the set.
        """
        self.processing.discard(phone_number)

    async def close_all(self) -> None:
        """
        Gracefully close all active agent sessions.

        Disconnects all MCP connections and clears the sessions dictionary.
        Should be called during application shutdown to ensure clean cleanup.

        Side Effects:
            - Disconnects all agents
            - Clears sessions dictionary
            - Logs any disconnection errors

        Example:
            >>> await manager.close_all()
            # All MCP connections closed
        """
        for phone_number, agent in list(self.sessions.items()):
            try:
                await agent.disconnect()
            except Exception as e:
                logger.error(f"Error closing session for {phone_number}: {e}")
        self.sessions.clear()


async def is_mcp_server_healthy(mcp_server_url: str) -> bool:
    """
    Verify MCP server is reachable and responding correctly.

    Performs a health check by connecting to the MCP server and calling
    the is_healthy tool. Used by the /health endpoint to monitor system status.

    Args:
        mcp_server_url: URL of the MCP server to check

    Returns:
        bool: True if server is healthy, False otherwise

    Example:
        >>> await is_mcp_server_healthy("http://localhost:8000/mcp")
        True

    Note:
        Returns False if connection fails or health check returns non-ok status.
    """
    try:
        async with streamablehttp_client(mcp_server_url) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool("is_healthy", {})
                return result.get("status") == "ok"
    except Exception as e:
        logger.error(f"MCP health check failed: {e}")
        return False


def check_missing_env_vars() -> tuple[list[str], bool]:
    """
    Validate that all required environment variables are set.

    Returns:
        Tuple containing:
            - List of missing environment variable names
            - Boolean indicating if all required vars are present

    Example:
        >>> missing, ok = check_missing_env_vars()
        >>> if not ok:
        ...     print(f"Missing: {missing}")
        Missing: ['GROQ_API_KEY']
    """
    required_env_vars = [
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_WHATSAPP_NUMBER",
        "GROQ_API_KEY",
    ]
    missing_env_vars = [var for var in required_env_vars if not os.environ.get(var)]
    env_ok = not missing_env_vars
    return missing_env_vars, env_ok


async def process_message_task(
    agent: AskariAgent,
    phone_number: str,
    message: str,
    message_sid: str,
    session_manager: SessionManager,
    rate_limiter: RateLimiter,
    num_media: int,
) -> None:
    """
    Background task for processing WhatsApp messages asynchronously.

    This function runs as a FastAPI background task, allowing the webhook
    endpoint to return immediately to Twilio while message processing continues.
    Handles the complete message lifecycle including:
    - Typing indicator
    - Media validation
    - Rate limit checking
    - Agent processing
    - Response delivery
    - Error handling

    Args:
        agent: The AskariAgent instance for this user
        phone_number: User's phone number (E.164 format without whatsapp: prefix)
        message: The message text from the user
        message_sid: Twilio message identifier for typing indicator
        session_manager: Session manager to update processing state
        rate_limiter: Rate limiter to check message limits
        num_media: Number of media attachments (0 for text-only)

    Side Effects:
        - Sends typing indicator via Twilio
        - Sends WhatsApp response message
        - Updates session manager processing state
        - Reports errors to Rollbar
        - Logs processing events

    Example:
        >>> background_tasks.add_task(
        ...     process_message_task,
        ...     agent, "+1234567890", "Hello", "SM123", manager, limiter, 0
        ... )
    """
    try:
        # Mark as processing to prevent concurrent handling
        session_manager.start_processing(phone_number)

        # Send typing indicator for better UX
        await send_typing_indicator_safe(message_sid)

        # Determine response based on validation and processing
        response_text = await determine_response(
            agent, phone_number, message, num_media, rate_limiter
        )

        # Send WhatsApp reply
        await send_whatsapp_message(phone_number, response_text)

    finally:
        # Always mark as finished, even on error
        session_manager.finish_processing(phone_number)


async def send_typing_indicator_safe(message_sid: str) -> None:
    """
    Send WhatsApp typing indicator with error handling.

    Args:
        message_sid: Twilio message identifier

    Side Effects:
        Logs warning if typing indicator fails
    """
    try:
        send_typing_indicator(
            message_sid,
            account_sid=TWILIO_ACCOUNT_SID,
            auth_token=TWILIO_AUTH_TOKEN,
        )
    except Exception as e:
        logger.warning(f"Typing indicator failed: {e}")


async def determine_response(
    agent: AskariAgent,
    phone_number: str,
    message: str,
    num_media: int,
    rate_limiter: RateLimiter,
) -> str:
    """
    Determine the appropriate response based on validation and processing.

    Applies validation rules in order:
    1. Check for media attachments (not supported)
    2. Check rate limits
    3. Process message with agent

    Args:
        agent: The AskariAgent instance
        phone_number: User's phone number
        message: The message text
        num_media: Number of media attachments
        rate_limiter: Rate limiter instance

    Returns:
        str: The response text to send to the user

    Example:
        >>> response = await determine_response(agent, "+1234567890", "Hello", 0, limiter)
        >>> print(response)
        "Hello! How can I help you?"
    """
    # Check for media attachments
    if num_media > 0:
        logger.info(f"Rejected media message from {phone_number}")
        return MSG_MEDIA_NOT_SUPPORTED

    # Check rate limit
    if rate_limiter.is_rate_limited(phone_number):
        remaining_time = rate_limiter.get_remaining_time(phone_number)
        logger.warning(f"Rate limit exceeded for {phone_number}")
        return MSG_RATE_LIMITED.format(remaining_time)

    # Process the message
    return await process_with_agent(agent, message, phone_number)


async def process_with_agent(
    agent: AskariAgent, message: str, phone_number: str
) -> str:
    """
    Process message with the agent and handle errors.

    Args:
        agent: The AskariAgent instance
        message: The message text to process
        phone_number: User's phone number (for logging)

    Returns:
        str: Agent response or error message

    Side Effects:
        - Reports errors to Rollbar
        - Logs processing errors
    """
    try:
        return await agent.run(message)
    except Exception as e:
        logger.error(f"Agent processing error for {phone_number}: {e}")
        await report_error_to_rollbar_async(exc=e)
        return MSG_PROCESSING_ERROR


async def send_whatsapp_message(phone_number: str, message_text: str) -> None:
    """
    Send a WhatsApp message via Twilio.

    Args:
        phone_number: Recipient's phone number (E.164 format without prefix)
        message_text: Message content to send

    Side Effects:
        - Sends message via Twilio API
        - Logs message delivery

    Example:
        >>> await send_whatsapp_message("+1234567890", "Hello!")
    """
    chunks = split_whatsapp_message(message_text)

    for i, chunk in enumerate(chunks):
        try:
            twilio_client.messages.create(
                from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
                body=chunk,
                to=f"whatsapp:{phone_number}",
            )
            logger.info(f"Sent response to {phone_number} (chunk {i+1}/{len(chunks)})")
        except Exception as e:
            logger.error(f"Failed to send chunk {i+1} to {phone_number}: {e}")
            raise e


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Initializes all application components including session manager,
    rate limiter, and Rollbar integration. Defines all HTTP endpoints
    and lifecycle handlers.

    Returns:
        FastAPI: Configured application instance ready to serve

    Example:
        >>> app = create_app()
        >>> # Use with uvicorn or gunicorn
    """
    session_manager = SessionManager(
        mcp_server_url=MCP_SERVER_URL,
        instructions=WHATSAPP_SYSTEM_PROMPT,
    )

    rate_limiter = RateLimiter(
        max_messages=RATE_LIMIT_MESSAGES,
        window_seconds=RATE_LIMIT_WINDOW,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """
        Application lifespan manager for graceful startup/shutdown.

        Ensures all MCP connections are properly closed when the server stops.
        """
        yield
        await session_manager.close_all()

    # Initialize Rollbar for error tracking
    is_rollbar_initialized = initialize_rollbar()

    # Create FastAPI app
    app = FastAPI(title="Askari WhatsApp Bot", lifespan=lifespan)

    if is_rollbar_initialized:
        rollbar_add_to(app)

    @app.post("/webhook")
    async def webhook(
        background_tasks: BackgroundTasks,
        From: str = Form(...),
        Body: str = Form(...),
        MessageSid: str = Form(...),
        NumMedia: int = Form(0),
    ):
        """
        Twilio webhook endpoint for incoming WhatsApp messages.

        Receives WhatsApp messages from Twilio, validates concurrent processing,
        retrieves or creates agent session, and queues message processing as
        a background task.

        Args:
            background_tasks: FastAPI background task manager
            From: Sender's WhatsApp number (format: whatsapp:+1234567890)
            Body: Message text content
            MessageSid: Twilio message identifier
            NumMedia: Number of media attachments (default: 0)

        Returns:
            PlainTextResponse: Empty XML response (Twilio requirement)

        Side Effects:
            - Sends "processing previous message" warning if concurrent
            - Creates/retrieves agent session
            - Queues background processing task

        Example:
            # Twilio sends POST request:
            # From: whatsapp:+1234567890
            # Body: Hello
            # MessageSid: SM123
            # -> Responds immediately, processes in background
        """
        phone_number = From.replace("whatsapp:", "")

        # Check for concurrent message processing
        if session_manager.is_processing(phone_number):
            logger.info(f"Message already being processed for {phone_number}")
            await send_whatsapp_message(phone_number, MSG_PROCESSING_PREVIOUS)
            return PlainTextResponse("", media_type="application/xml")

        # Retrieve or create persistent agent session
        agent = await session_manager.get_or_create_session(phone_number)

        # Queue message processing as background task
        background_tasks.add_task(
            process_message_task,
            agent,
            phone_number,
            Body,
            MessageSid,
            session_manager,
            rate_limiter,
            NumMedia,
        )

        # Respond immediately to Twilio (required within 15 seconds)
        return PlainTextResponse("", media_type="application/xml")

    @app.get("/health")
    async def health():
        """
        Health check endpoint for monitoring and load balancers.

        Validates:
        - Required environment variables are set
        - MCP server is reachable and healthy

        Returns:
            JSONResponse: Health status with HTTP 200 (healthy) or 503 (unhealthy)

        Example:
            >>> response = await client.get("/health")
            >>> response.json()
            {
                "env_status": "ok",
                "mcp_server_alive": true
            }
        """
        missing_env_vars, env_ok = check_missing_env_vars()
        mcp_ok = await is_mcp_server_healthy(MCP_SERVER_URL)

        status_code = 200 if env_ok and mcp_ok else 503

        return JSONResponse(
            {
                "env_status": "ok"
                if env_ok
                else f"missing: {', '.join(missing_env_vars)}",
                "mcp_server_alive": mcp_ok,
            },
            status_code=status_code,
        )

    @app.get("/error")
    async def read_error():
        """
        Test endpoint for error tracking validation.

        Deliberately raises an exception to test Rollbar integration.
        Should only be used in development/testing environments.

        Raises:
            ZeroDivisionError: Always raises this exception
        """
        return 1 / 0

    return app


def main():
    """
    Entry point for running the server directly.

    Starts Uvicorn server on all interfaces (0.0.0.0) port 8001.
    For production, use Gunicorn with Uvicorn workers instead.

    Example:
        $ python -m askari_patrol_client.server
        INFO: Started server process [12345]
        INFO: Waiting for application startup.
    """
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()

import logging
import os
from contextlib import asynccontextmanager

import rollbar
from common.utils import send_typing_indicator
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

TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_WHATSAPP_NUMBER = os.environ["TWILIO_WHATSAPP_NUMBER"]
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8000/mcp")
ROLLBAR_SERVER_TOKEN = os.environ.get("ROLLBAR_SERVER_TOKEN")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


async def is_mcp_server_healthy(mcp_server_url: str) -> bool:
    async with streamablehttp_client(mcp_server_url) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool("is_healthy", {})
            return result.get("status") == "ok"


def check_missing_env_vars() -> tuple[list, bool]:
    required_env_vars = [
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_WHATSAPP_NUMBER",
        "GROQ_API_KEY",
    ]
    missing_env_vars = [var for var in required_env_vars if not os.environ.get(var)]
    env_ok = not missing_env_vars
    return missing_env_vars, env_ok


class SessionManager:
    """Maintains one persistent AskariAgent per phone number."""

    def __init__(self, mcp_server_url: str, instructions: str):
        self.mcp_server_url = mcp_server_url
        self.instructions = instructions
        self.sessions: dict[str, AskariAgent] = {}

    async def get_or_create_session(self, phone_number: str) -> AskariAgent:
        """Get or create a long-lived AskariAgent."""
        if phone_number not in self.sessions:
            logger.info(f"Creating new agent session for {phone_number}")
            agent = AskariAgent(
                server_url=self.mcp_server_url,
                instructions=self.instructions,
            )
            await agent.connect()
            self.sessions[phone_number] = agent

        return self.sessions[phone_number]

    async def close_all(self):
        """Gracefully close all MCP connections."""
        for pn, agent in list(self.sessions.items()):
            try:
                await agent.disconnect()
            except Exception as e:
                logger.error(f"Error closing session for {pn}: {e}")
        self.sessions.clear()


async def process_message_task(
    agent: AskariAgent,
    phone_number: str,
    message: str,
    message_sid: str,
):
    """
    Runs in background (inside same FastAPI process).
    Uses the persistent agent from SessionManager.
    """

    # Send WhatsApp typing indicator
    try:
        send_typing_indicator(
            message_sid,
            account_sid=TWILIO_ACCOUNT_SID,
            auth_token=TWILIO_AUTH_TOKEN,
        )
    except Exception as e:
        logger.warning(f"Typing indicator failed: {e}")

    # Run message through the persistent agent (with context)
    try:
        response_text = await agent.run(message)
    except Exception as e:
        logger.error(f"Agent processing error: {e}")
        response_text = "I encountered an error processing your message."

    # Send WhatsApp reply
    twilio_client.messages.create(
        from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
        body=response_text,
        to=f"whatsapp:{phone_number}",
    )
    logger.info(f"Sent response to {phone_number}")


def create_app():
    session_manager = SessionManager(
        mcp_server_url=MCP_SERVER_URL,
        instructions=WHATSAPP_SYSTEM_PROMPT,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        await session_manager.close_all()

    # Initialize Rollbar SDK with your server-side access token
    if ROLLBAR_SERVER_TOKEN:
        rollbar.init(ROLLBAR_SERVER_TOKEN)
    else:
        logger.warning(
            "Failed to initialize rollbar due to missing rollbar server side access token. Ensure ROLLBAR_SERVER_TOKEN env variable is set"
        )

    app = FastAPI(title="Askari WhatsApp Bot", lifespan=lifespan)
    if ROLLBAR_SERVER_TOKEN:
        rollbar_add_to(app)

    @app.post("/webhook")
    async def webhook(
        background_tasks: BackgroundTasks,
        From: str = Form(...),
        Body: str = Form(...),
        MessageSid: str = Form(...),
    ):
        phone_number = From.replace("whatsapp:", "")

        # Retrieve existing agent or create new one
        agent = await session_manager.get_or_create_session(phone_number)

        # Push message processing into background task
        background_tasks.add_task(
            process_message_task,
            agent,
            phone_number,
            Body,
            MessageSid,
        )

        # Respond instantly to Twilio (empty XML)
        return PlainTextResponse("", media_type="application/xml")

    @app.get("/health")
    async def health():
        missing_env_vars, env_ok = check_missing_env_vars()
        try:
            mcp_ok = await is_mcp_server_healthy(MCP_SERVER_URL)
        except Exception:
            mcp_ok = False

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
        return 1 / 0

    return app


def main():
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()

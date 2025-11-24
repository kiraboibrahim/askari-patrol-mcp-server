import logging
import os
from contextlib import asynccontextmanager

from common.utils import send_typing_indicator
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, PlainTextResponse
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from twilio.twiml.messaging_response import MessagingResponse

from .agent import AskariAgent

logger = logging.getLogger("openai.agents")
logger.setLevel(logging.DEBUG)

TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]


async def is_mcp_server_healthy(mcp_server_url: str) -> bool:
    async with streamablehttp_client(mcp_server_url) as (
        read_stream,
        write_stream,
        _,
    ):
        # Create a session using the client streams
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            await session.initialize()
            # Call the is_healthy tool
            result = await session.call_tool("is_healthy", {})
            return result.get("status") == "ok"


def check_missing_env_vars() -> list:
    required_env_vars = [
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_WHATSAPP_NUMBER",
        "GROQ_API_KEY",
    ]
    missing_env_vars = [var for var in required_env_vars if not os.environ.get(var)]
    env_ok = not missing_env_vars
    return missing_env_vars, env_ok


def create_app(
    mcp_server_url: str = "http://localhost:8000/mcp",
    instructions: str = None,
):
    """Create FastAPI app with Twilio WhatsApp webhook."""

    agent = AskariAgent(
        server_url=mcp_server_url,
        instructions=instructions or AskariAgent.DEFAULT_INSTRUCTIONS,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await agent.connect()
        yield
        await agent.disconnect()

    app = FastAPI(title="Askari WhatsApp Bot", lifespan=lifespan)

    @app.post("/webhook")
    async def webhook(
        From: str = Form(...),
        Body: str = Form(...),
        MessageSid: str = Form(...),
    ):
        """Handle incoming Twilio WhatsApp messages."""
        # phone = From.replace("whatsapp:", "")
        try:
            # This feature is still in beta and thus not stable, if any errors occur, don't halt process
            send_typing_indicator(
                MessageSid, account_sid=TWILIO_ACCOUNT_SID, auth_token=TWILIO_AUTH_TOKEN
            )
        except Exception:
            pass

        response_text = await agent.run(Body)

        twiml = MessagingResponse()
        twiml.message(response_text)
        return PlainTextResponse(str(twiml), media_type="application/xml")

    @app.get("/health")
    async def health():
        missing_env_vars, env_ok = check_missing_env_vars()
        try:
            mcp_ok = await is_mcp_server_healthy(mcp_server_url)
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

    return app


def main():
    import os

    import uvicorn

    from .prompts import WHATSAPP_CLIENT_INSTRUCTIONS

    app = create_app(
        mcp_server_url=os.environ.get("MCP_SERVER_URL", "http://localhost:8000/mcp"),
        instructions=WHATSAPP_CLIENT_INSTRUCTIONS,
    )
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()

from contextlib import asynccontextmanager

from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse

from .agent import AskariAgent


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
    ):
        """Handle incoming Twilio WhatsApp messages."""
        # phone = From.replace("whatsapp:", "")
        response_text = await agent.run(Body)

        twiml = MessagingResponse()
        twiml.message(response_text)
        return PlainTextResponse(str(twiml), media_type="application/xml")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


def main():
    import os

    import uvicorn

    app = create_app(
        mcp_server_url=os.environ.get("MCP_SERVER_URL", "http://localhost:8000/mcp")
    )
    uvicorn.run(app, host="0.0.0.0", port=8001)

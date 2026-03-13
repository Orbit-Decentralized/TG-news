"""
Telegram Bot Webhook Server
For Cloud Run Service, handle Telegram commands
"""
import os
import logging
import html
import asyncio

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route
from starlette.requests import Request
import uvicorn

from telegram import Bot, Update
from telegram.constants import ParseMode

import config
from db import init_db

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

bot = Bot(token=config.TELEGRAM_BOT_TOKEN)


# ── Command handlers ──────────────────────────────────────────────────

async def handle_start(update: Update):
    await bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "🔮 Prediction market news tracker is now running!\n\n"
            "I will scan the following sources every hour for prediction market news:\n"
            "📰 CoinDesk, CoinTelegraph, The Block, Decrypt\n"
            "🐦 Twitter: @Polymarket, @Kalshi, etc.\n\n"
            "Commands:\n"
            "/status - View bot status\n"
            "/sources - View tracked sources"
        ),
    )


async def handle_status(update: Update):
    twitter_status = "✅ Configured" if config.TWITTER_USERNAME else "❌ Not configured"
    await bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "📊 Bot status\n\n"
            f"Scan interval: hourly (Cloud Scheduler)\n"
            f"RSS sources: {len(config.RSS_FEEDS)}\n"
            f"Twitter: {twitter_status}\n"
            f"Tracked keywords: {len(config.KEYWORDS)}"
        ),
    )


async def handle_sources(update: Update):
    rss_list = "\n".join(f"  • {name}" for name in config.RSS_FEEDS)
    tw_list = "\n".join(f"  • @{acc}" for acc in config.TWITTER_ACCOUNTS)
    await bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"📰 RSS sources:\n{rss_list}\n\n🐦 Twitter accounts:\n{tw_list}",
    )


COMMAND_HANDLERS = {
    "/start": handle_start,
    "/status": handle_status,
    "/sources": handle_sources,
}


# ── HTTP routes ─────────────────────────────────────────────────

async def health_check(request: Request):
    return PlainTextResponse("OK")


async def webhook_handler(request: Request):
    """Handle Telegram webhook requests"""
    try:
        data = await request.json()
        update = Update.de_json(data, bot)
        
        if update.message and update.message.text:
            text = update.message.text
            command = text.split()[0] if text else ""
            
            handler = COMMAND_HANDLERS.get(command)
            if handler:
                await handler(update)
        
        return Response(status_code=200)
    
    except Exception as e:
        logger.error(f"Webhook handling failed: {e}")
        return Response(status_code=200)  # Return 200 to prevent Telegram retries


async def startup():
    await init_db()
    logger.info("🤖 Webhook server started")


app = Starlette(
    routes=[
        Route("/", health_check, methods=["GET"]),
        Route("/webhook", webhook_handler, methods=["POST"]),
    ],
    on_startup=[startup],
)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

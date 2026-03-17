import asyncio
import json
import logging
import html
import os
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib import request as urllib_request

from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config


# Cloud Run health check HTTP server
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass  # suppress logs


def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logging.getLogger(__name__).info(f"Health check server started on port {port}")


from db import init_db, is_sent, mark_sent
from sources.rss_fetcher import fetch_rss_news
from sources.twitter_fetcher import fetch_twitter_news

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _strip_unsupported_tags(text: str) -> str:
    # Keep textual content, remove all HTML/XML-like tags
    return re.sub(r"<[^>]+>", "", text or "")


def _translate_title_summary_sync(title: str, summary: str) -> str:
    if not config.OPENROUTER_KEY:
        return ""

    combined_text = f"{title}\n{summary}"
    prompt = (
        "Translate the following content into natural English. "
        "The first line is title and the second line is summary. "
        "Remove all unsupported Telegram/HTML tags but preserve the full textual meaning. "
        "Return only translated text, no explanation.\n\n"
        f"{combined_text}"
    )

    payload = {
        "model": config.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "You are a precise translation assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }

    req = urllib_request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.OPENROUTER_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"].strip()
        return _strip_unsupported_tags(content)
    except Exception as e:
        logger.warning(f"OpenRouter translation failed, skip translated text: {e}")
        return ""


async def _with_translated_text(news: dict) -> dict:
    translated_text = await asyncio.to_thread(
        _translate_title_summary_sync,
        news["title"],
        news["summary"] if news["summary"] else "",
    )

    if not translated_text:
        return news

    translated_news = dict(news)
    translated_news["translated_text"] = translated_text
    return translated_news


def format_message(news: dict) -> str:
    """Format a single news item into a Telegram message."""
    icon = "🐦" if news["type"] == "twitter" else "📰"
    source = html.escape(news["source"])
    title = html.escape(news["title"])
    raw_summary = news["summary"] if news["summary"] else ""
    summary = html.escape(_strip_unsupported_tags(raw_summary)) if raw_summary else ""
    translated_text = html.escape(news.get("translated_text", ""))
    url = news["url"]
    published = news.get("published", "")

    lines = [
        f"{icon} <b>【{source}】</b>",
        f"{title}",
    ]

    if summary and summary != title:
        # Trim overly long summary
        if len(summary) > 150:
            summary = summary[:150] + "..."
        lines.append(f"\n{summary}")

    if translated_text:
        if len(translated_text) > 150:
            translated_text = translated_text[:150] + "..."
        lines.append(f"\n🌐 {translated_text}")

    lines.append(f'\n🔗 <a href="{url}">Read full article</a>')

    if published:
        lines.append(f"⏰ {published}")

    return "\n".join(lines)


async def scan_and_send(bot: Bot):
    """Scan all sources and send new messages."""
    logger.info("Starting news scan...")

    # Fetch all sources in parallel
    rss_task = fetch_rss_news()
    twitter_task = fetch_twitter_news()
    rss_news, twitter_news = await asyncio.gather(rss_task, twitter_task)

    all_news = rss_news + twitter_news
    sent_count = 0

    for news in all_news:
        if await is_sent(news["id"]):
            continue

        try:
            news_with_translation = await _with_translated_text(news)
            msg = format_message(news_with_translation)
            await bot.send_message(
                chat_id=config.TELEGRAM_CHAT_ID,
                text=msg,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False,
            )
            await mark_sent(
                news["id"],
                news["source"],
                news["title"],
                news["url"],
                news.get("summary", "") or "",
                news_with_translation.get("translated_text", "") or "",
            )
            sent_count += 1

            # Avoid triggering Telegram rate limits
            await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Send failed: {news['title'][:50]} - {e}")

    logger.info(f"Scan complete, sent {sent_count} new messages")


# ── Telegram commands ──────────────────────────────────────────


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔮 Prediction market news tracker is now running!\n\n"
        "I will scan the following sources every hour for prediction market news:\n"
        "📰 CoinDesk, CoinTelegraph, The Block, Decrypt\n"
        "🐦 Twitter: @Polymarket, @Kalshi, etc.\n\n"
        "Commands:\n"
        "/scan - Run a scan now\n"
        "/status - View bot status\n"
        "/sources - View tracked sources"
    )


async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Scanning, please wait...")
    await scan_and_send(context.bot)
    await update.message.reply_text("✅ Scan completed!")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    twitter_status = "✅ Configured" if config.TWITTER_USERNAME else "❌ Not configured"
    await update.message.reply_text(
        "📊 Bot status\n\n"
        f"Scan interval: every {config.SCAN_INTERVAL // 60} minutes\n"
        f"RSS sources: {len(config.RSS_FEEDS)}\n"
        f"Twitter: {twitter_status}\n"
        f"Tracked keywords: {len(config.KEYWORDS)}"
    )


async def cmd_sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rss_list = "\n".join(f"  • {name}" for name in config.RSS_FEEDS)
    tw_list = "\n".join(f"  • @{acc}" for acc in config.TWITTER_USERS)
    await update.message.reply_text(
        f"📰 RSS sources:\n{rss_list}\n\n" f"🐦 Twitter accounts:\n{tw_list}"
    )


# ── Main ─────────────────────────────────────────────────


async def post_init(app):
    """Initialize scheduler after the application starts."""
    await init_db()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scan_and_send,
        "interval",
        seconds=config.SCAN_INTERVAL,
        args=[app.bot],
        id="news_scanner",
    )
    scheduler.start()
    logger.info(
        f"Scheduler started, scanning every {config.SCAN_INTERVAL // 60} minutes"
    )

    # Scan once at startup
    asyncio.create_task(scan_and_send(app.bot))


def main():
    # Start Cloud Run health check server
    start_health_server()

    if not config.TELEGRAM_BOT_TOKEN:
        print("❌ Please set TELEGRAM_BOT_TOKEN first; see .env.example")
        return
    if not config.TELEGRAM_CHAT_ID:
        print("❌ Please set TELEGRAM_CHAT_ID first; see .env.example")
        return

    app = (
        ApplicationBuilder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("scan", cmd_scan))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("sources", cmd_sources))

    logger.info("🤖 Bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

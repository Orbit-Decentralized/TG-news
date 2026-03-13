"""
News scanning script
For Cloud Run Job, triggered by Cloud Scheduler
"""
import asyncio
import logging
import html

from telegram import Bot
from telegram.constants import ParseMode

import config
from db import init_db, is_sent, mark_sent, get_recent_titles
from sources.rss_fetcher import fetch_rss_news
from sources.twitter_fetcher import fetch_twitter_news

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
import re
from difflib import SequenceMatcher
from deep_translator import GoogleTranslator

translator = GoogleTranslator(source='auto', target='en')


def contains_chinese(text: str) -> bool:
    """Check whether text contains Chinese characters"""
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def translate_to_english(text: str) -> str:
    """Translate Chinese to English"""
    try:
        return translator.translate(text)
    except Exception as e:
        logger.warning(f"Translation failed: {e}")
        return ""


def _normalize(text: str) -> str:
    """Normalize title for comparison"""
    text = text.lower().strip()
    # Remove common prefix markers
    text = re.sub(r'^(breaking|速報|快訊|獨家)[:\s：]*', '', text)
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    return text


def is_duplicate(title: str, existing_titles: list[str], threshold: float = 0.6) -> bool:
    """Check if title is similar to existing titles (cross-source dedup)"""
    norm_new = _normalize(title)
    if not norm_new:
        return False
    for existing in existing_titles:
        norm_existing = _normalize(existing)
        if not norm_existing:
            continue
        ratio = SequenceMatcher(None, norm_new, norm_existing).ratio()
        if ratio >= threshold:
            logger.info(f"Dedup: \"{title[:40]}\" vs \"{existing[:40]}\" similarity {ratio:.2f}")
            return True
    return False


def strip_html(text: str) -> str:
    """Remove HTML tags and unescape entities"""
    text = re.sub(r'<br\s*/?>', '\n', text)  # <br/> to newline
    text = re.sub(r'<[^>]+>', '', text)       # Remove all HTML tags
    text = html.unescape(text)                # Unescape entities like &amp;
    text = re.sub(r'\n{3,}', '\n\n', text)    # Collapse extra blank lines
    return text.strip()


def format_message(news: dict) -> str:
    """Format a single news item into a Telegram message."""
    icon = "🐦" if news["type"] == "twitter" else "📰"
    source = html.escape(news["source"])
    url = news["url"]
    published = news.get("published", "")

    # Strip HTML tags
    title_clean = strip_html(news["title"])
    summary_clean = strip_html(news["summary"]) if news["summary"] else ""

    # First line: source + time
    header = f"{icon} <b>{source}</b>"
    if published:
        header += f" | 🕒 {published}"

    # Link
    link_line = f'🔗 <a href="{url}">Source</a>'

    lines = [header, link_line, ""]

    # Content: Chinese + English translation
    content = title_clean
    if summary_clean and summary_clean != title_clean:
        if len(summary_clean) > 200:
            summary_clean = summary_clean[:200] + "..."
        content = f"{title_clean}\n{summary_clean}"

    if contains_chinese(content):
        lines.append(f"🇨🇳 {html.escape(content)}")
        translated = translate_to_english(content[:300])
        if translated:
            lines.append(f"🇺🇸 {html.escape(translated)}")
    else:
        lines.append(html.escape(content))

    return "\n".join(lines)


async def scan_and_send():
    """Scan all sources and send new messages."""
    logger.info("Starting news scan...")
    
    await init_db()
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)

    # Get recent sent titles for dedup
    recent_titles = await get_recent_titles(hours=48)
    logger.info(f"Loaded {len(recent_titles)} historical titles for dedup")

    # Fetch all sources in parallel
    rss_task = fetch_rss_news()
    twitter_task = fetch_twitter_news()
    rss_news, twitter_news = await asyncio.gather(rss_task, twitter_task)

    all_news = rss_news + twitter_news
    sent_count = 0
    skipped_dup = 0

    for news in all_news:
        if await is_sent(news["id"]):
            continue

        # Cross-source title dedup
        if is_duplicate(news["title"], recent_titles):
            await mark_sent(news["id"], news["source"], news["title"], news["url"])
            skipped_dup += 1
            continue

        try:
            msg = format_message(news)
            await bot.send_message(
                chat_id=config.TELEGRAM_CHAT_ID,
                text=msg,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False,
            )
            await mark_sent(news["id"], news["source"], news["title"], news["url"])
            recent_titles.append(news["title"])  # Append to avoid duplicates in same batch
            sent_count += 1

            # Avoid triggering Telegram rate limits
            await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Send failed: {news['title'][:50]} - {e}")

    logger.info(f"Scan complete, sent {sent_count} messages, skipped {skipped_dup} by dedup")


def main():
    if not config.TELEGRAM_BOT_TOKEN:
        print("❌ Please set TELEGRAM_BOT_TOKEN first")
        return
    if not config.TELEGRAM_CHAT_ID:
        print("❌ Please set TELEGRAM_CHAT_ID first")
        return

    asyncio.run(scan_and_send())
    print("✅ Scan task completed")


if __name__ == "__main__":
    main()

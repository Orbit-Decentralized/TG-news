import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone

import feedparser

from config import KEYWORDS, RSS_FEEDS

logger = logging.getLogger(__name__)


def _matches_keywords(text: str) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in KEYWORDS)


def _make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


async def fetch_rss_news() -> list[dict]:
    """Fetch prediction-market-related news from all RSS sources."""
    results = []
    
    # Set 24-hour cutoff
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)

    for source_name, feed_url in RSS_FEEDS.items():
        try:
            # feedparser is synchronous; use to_thread to avoid blocking
            feed = await asyncio.to_thread(feedparser.parse, feed_url)

            for entry in feed.entries[:30]:  # Limit to 30 items per source
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                link = entry.get("link", "")

                if not _matches_keywords(f"{title} {summary}"):
                    continue

                # Parse publish time
                published = ""
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    # Filter out items older than 24 hours
                    if dt < cutoff_time:
                        continue
                    published = dt.strftime("%Y-%m-%d %H:%M UTC")

                results.append({
                    "id": _make_id(link),
                    "source": source_name,
                    "title": title,
                    "summary": summary[:200] if summary else "",
                    "url": link,
                    "published": published,
                    "type": "rss",
                })

        except Exception as e:
            logger.warning(f"Failed to fetch {source_name} RSS: {e}")

    logger.info(f"RSS: found {len(results)} related items")
    return results

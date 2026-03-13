import asyncio
import hashlib
import logging
import os

from config import KEYWORDS, TWITTER_USERS, TWITTER_EMAIL, TWITTER_PASSWORD, TWITTER_USERNAME

logger = logging.getLogger(__name__)

COOKIES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "twikit_cookies.json")


def _matches_keywords(text: str) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in KEYWORDS)


def _make_id(tweet_id: str) -> str:
    return hashlib.md5(f"tweet_{tweet_id}".encode()).hexdigest()


async def fetch_twitter_news() -> list[dict]:
    """Fetch tweets related to prediction markets from tracked Twitter accounts."""
    if not all([TWITTER_USERNAME, TWITTER_EMAIL, TWITTER_PASSWORD]):
        logger.info("Twitter login info not set; skipping Twitter source")
        return []

    try:
        from twikit import Client
    except ImportError:
        logger.warning("twikit not installed; skipping Twitter source. Run: pip install twikit")
        return []

    results = []
    client = Client("en-US")

    try:
        # Try to load saved cookies
        if os.path.exists(COOKIES_PATH):
            client.load_cookies(COOKIES_PATH)
            logger.info("Loaded Twitter cookies")
        else:
            await client.login(
                auth_info_1=TWITTER_USERNAME,
                auth_info_2=TWITTER_EMAIL,
                password=TWITTER_PASSWORD,
            )
            client.save_cookies(COOKIES_PATH)
            logger.info("Twitter login successful, cookies saved")

        for account in TWITTER_USERS:
            try:
                user = await client.get_user_by_screen_name(account)
                tweets = await client.get_user_tweets(user.id, "Tweets", count=10)

                for tweet in tweets:
                    text = tweet.text or ""

                    # Tweets from official prediction market accounts are all included; no keyword filter needed
                    # Only other accounts need filtering
                    tweet_url = f"https://x.com/{account}/status/{tweet.id}"

                    results.append({
                        "id": _make_id(str(tweet.id)),
                        "source": f"𝕏 @{account}",
                        "title": text[:100] + ("..." if len(text) > 100 else ""),
                        "summary": text[:280],
                        "url": tweet_url,
                        "published": tweet.created_at or "",
                        "type": "twitter",
                    })

            except Exception as e:
                logger.warning(f"Failed to fetch tweets from @{account}: {e}")
                continue

            # Avoid overly frequent requests
            await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"Twitter connection failed: {e}")

    logger.info(f"Twitter: found {len(results)} tweets")
    return results

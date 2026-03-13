import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Twitter login (optional; if missing, Twitter source will be skipped)
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME", "")
TWITTER_EMAIL = os.getenv("TWITTER_EMAIL", "")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD", "")

# Scan interval (seconds)
SCAN_INTERVAL = 3600  # 1 hour

# RSS sources (Chinese-language media only)
RSS_FEEDS = {
    # General crypto media
    "PANews": "https://www.panewslab.com/rss.xml",
    "BlockBeats Rhythm": "https://api.theblockbeats.news/v2/rss/all",
    "Odaily Planet Daily": "https://rss.odaily.news/rss/newsflash",
    "ChainCatcher": "https://rsshub.app/chaincatcher/news",
    "Foresight News": "https://rsshub.app/foresightnews/news",
    "Equation News": "https://rss-public.bwe-ws.com/",
    # Taiwan / Traditional Chinese
    "BlockTempo": "https://rsshub.app/blocktempo",
    "ABMedia Chain News": "https://www.abmedia.io/feed",
    # Mainland major media
    "Jinse Finance Flash News": "https://rss.web30.lol/jinse/lives",
    "Jinse Finance Articles": "https://rss.web30.lol/jinse2",
    "TechFlow": "https://rsshub.app/techflowpost",
    "Wu Talks Blockchain": "https://rsshub.app/wublock123",
    "MarsBit": "https://rsshub.app/marsbit/news",
    "TokenInsight": "https://rsshub.app/tokeninsight/news",
    "BitPush": "https://rsshub.app/bitpush/news",
    "Web3Caff": "https://rsshub.app/web3caff/news",
    "MetaEra": "https://rsshub.app/metaera/news",
}

# Twitter tracked accounts
TWITTER_USERS = [
    "Polymarket",
    "Kalshi",
    "ManifoldMarkets",
    "Metaculus",
    "ElectionBetting",
    "Domahhhh",  # Polymarket CEO
    "limitless_fdn",
    "myriad_market",
    "pmxtrade",
    "buzzing_cc",
    "opinionlabsxyz",
]

# Keyword filter (case-insensitive)
KEYWORDS = [
    # Platform names
    "polymarket",
    "kalshi",
    "predictit",
    "augur",
    "manifold",
    "metaculus",
    "gnosis prediction",
    "azuro",
    "limitless",
    "myriad",
    "pmx.trade",
    "buzzing",
    "opinion",
    # General terms
    "prediction market",
    "prediction markets",
    "betting market",
    "event contract",
    "event contracts",
    "forecast market",
    "forecasting market",
    "information market",
    "futarchy",
    # Chinese - core
    "預測市場",
    "事件合約",
    "博彩市場",
    "去中心化預測",
    "鏈上預測",
    "信息市場",
    # Chinese - trading and betting
    "賭盤",
    "賠率",
    "勝率",
    "押注",
    "下注",
    "投注",
    "對賭",
    "大選預測",
    "政治博弈",
]

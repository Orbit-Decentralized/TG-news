# Prediction Market News Tracking Telegram Bot - Implementation Plan

## Architecture Overview

```
[RSS Feeds] ──┐
               ├──> [News Aggregator] ──> [Keyword Filter] ──> [Telegram Bot] ──> You
[Twitter/X] ──┘         ↕
                   [SQLite DB]
                  (dedup / sent records)
```

## News Sources

### Crypto Media (RSS)
- CoinDesk: `https://www.coindesk.com/arc/outboundfeeds/rss/`
- CoinTelegraph: `https://cointelegraph.com/rss`
- The Block: `https://www.theblock.co/rss/all`
- Decrypt: `https://decrypt.co/feed`

### Twitter/X (free scraping via twikit)
Tracked accounts:
- @Polymarket, @Kalshi, @ManifoldMarkets
- @Metaculus, @PredictIt, @AugurProject, @gnosisdao

## Keyword Filter

Only news containing any of the following keywords will be pushed:
```
polymarket, kalshi, predictit, augur, manifold, metaculus, gnosis
prediction market, betting market, event contract, forecast market
prediction market, event contract
```

## Tech Stack
- Python 3.10+
- python-telegram-bot (v22+) - Telegram push
- feedparser - RSS parsing
- twikit - Twitter scraping (free, no API key required)
- aiosqlite - async SQLite (dedup)
- APScheduler - scheduling (hourly)

## File Structure
```
news-tracking-bot/
├── bot.py              # Main entry + Telegram bot
├── config.py           # Config (API keys, sources, keywords)
├── sources/
│   ├── rss_fetcher.py  # RSS news fetch
│   └── twitter_fetcher.py  # Twitter scraping
├── db.py               # SQLite DB operations
├── requirements.txt    # Dependencies
├── .env.example        # Environment variable example
└── .gitignore
```

## Push Format Example
```
📰 Prediction Market News

【CoinDesk】
Polymarket Sees Record Volume as US Election Bets Surge

Summary: Polymarket trading volume hit a new record...

🔗 https://coindesk.com/...
⏰ 2026-02-08 14:30
━━━━━━━━━━━━━━━
```

## Scheduling Logic
1. Run a scan once every hour
2. Fetch RSS feeds + Twitter posts
3. Filter relevant news by keywords
4. Check SQLite for dedup (avoid repeated pushes)
5. Send new messages via Telegram Bot

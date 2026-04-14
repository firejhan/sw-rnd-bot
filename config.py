import os

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "-1003970288441")
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
FB_ACCESS_TOKEN    = os.environ.get("FB_ACCESS_TOKEN", "")

CHECK_INTERVAL_HOURS = 24
DAILY_REPORT_HOUR    = 8
DAILY_REPORT_MINUTE  = 0

COMPETITORS = [
    {"name": "sureWin",  "promo_url": "https://www.mysurewin.com/en-my/promotion"},
    {"name": "Me88",     "promo_url": "https://www.me88diamond.com/en-my/promotion"},
    {"name": "BK8",      "promo_url": "https://www.bk8mlysia.com/en-my/promotion"},
    {"name": "Maxim88",  "promo_url": "https://www.maxim88msia.com/en-my/promotion"},
    {"name": "96M",      "promo_url": "https://www.96mas.com/en-my/promotion"},
    {"name": "Stake",    "promo_url": "https://stake.com/promotions"},
    {"name": "ECLBet",   "promo_url": "https://www.eclbet03.com/my/promotion"},
    {"name": "God55",    "promo_url": "https://www.god55.win/promotion"},
    {"name": "We1Win",   "promo_url": "https://www.we1win99.com/promotions"},
    {"name": "U88",      "promo_url": "https://www.u88game.com/en-my/promotion"},
    {"name": "8win",     "promo_url": "https://www.8win88.com/promotions"},
    {"name": "playX",    "promo_url": "https://www.myrplayx.win/en-my/promotion"},
    {"name": "maxwin",   "promo_url": "https://www.maxwinmy.com/en-my/promotion"},
]

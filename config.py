import os

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
FB_ACCESS_TOKEN    = os.environ.get("FB_ACCESS_TOKEN", "")

CHECK_INTERVAL_HOURS = 6
DAILY_REPORT_HOUR    = 8
DAILY_REPORT_MINUTE  = 0
SEND_TEST_ON_STARTUP = True

COMPETITORS = [
    {"name": "Me88",    "promo_url": "https://www.me88diamond.com/en-my/promotion",      "home_url": "https://www.me88diamond.com"},
    {"name": "BK8",     "promo_url": "https://www.bk8mlysia.com/en-my/promotion",        "home_url": "https://www.bk8mlysia.com"},
    {"name": "Maxim88", "promo_url": "https://www.maxim88msia.com/en-my/promotion",      "home_url": "https://www.maxim88msia.com"},
    {"name": "96M",     "promo_url": "https://www.96mas.com/en-my/promotion",            "home_url": "https://www.96mas.com"},
    {"name": "Stake",   "promo_url": "https://stake.com/promotions",                     "home_url": "https://stake.com"},
    {"name": "ECLBet",  "promo_url": "https://www.eclbet03.com/my/promotion",            "home_url": "https://www.eclbet03.com"},
    {"name": "God55",   "promo_url": "https://www.god55.win/promotion",                  "home_url": "https://www.god55.win"},
    {"name": "We1Win",  "promo_url": "https://www.we1win99.com/promotions",              "home_url": "https://www.we1win99.com"},
    {"name": "U88",     "promo_url": "https://www.u88game.com/en-my/promotion",          "home_url": "https://www.u88game.com"},
    {"name": "8win",    "promo_url": "https://www.8win88.com/promotions",                "home_url": "https://www.8win88.com"},
    {"name": "playX",   "promo_url": "https://www.myrplayx.win/en-my/promotion",        "home_url": "https://www.myrplayx.win"},
    {"name": "maxwin",  "promo_url": "https://www.maxwinmy.com/en-my/promotion",         "home_url": "https://www.maxwinmy.com"},
]

FB_AD_KEYWORDS = [
    "me88", "bk8", "maxim88", "96m casino", "eclbet",
    "god55", "we1win", "u88", "online casino malaysia",
    "malaysia casino", "trusted casino my",
]

OUR_BRANDS = {
    "sureWin": {"welcome_bonus": "100%首存红利", "min_deposit_myr": 30, "monthly_revenue": "RM32M-40M", "positioning": "信任/蓝勾/透明度"},
    "maxwin":  {"welcome_bonus": "100%首存红利", "min_deposit_myr": 30, "monthly_revenue": "RM6M",      "positioning": "大马最好玩"},
    "8win":    {"welcome_bonus": "首存红利",      "min_deposit_myr": 10, "monthly_revenue": "RM1M",      "positioning": "新平台快速成长"},
}

ANALYSIS_FOCUS = "我们是马来西亚 iGaming 运营商，旗下有 sureWin、maxwin、8win、playX、winX。目标市场：马来西亚华人玩家，25-45岁。"

import os

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
FB_ACCESS_TOKEN    = os.environ.get("FB_ACCESS_TOKEN", "")

CHECK_INTERVAL_HOURS = 3
DAILY_REPORT_HOUR    = 8
DAILY_REPORT_MINUTE  = 0

COMPETITORS = [
    {"name": "Me88",    "promo_url": "https://www.me88.com/promotion",     "home_url": "https://www.me88.com",    "fb_page_id": ""},
    {"name": "Maxim88", "promo_url": "https://www.maxim88.com/promotions", "home_url": "https://www.maxim88.com", "fb_page_id": ""},
    {"name": "BK8",     "promo_url": "https://www.bk8my.com/promotions",   "home_url": "https://www.bk8my.com",   "fb_page_id": ""},
]

OUR_BRANDS = {
    "sureWin": {"welcome_bonus": "100%首存红利", "min_deposit_myr": 30},
    "maxwin":  {"welcome_bonus": "100%首存红利", "min_deposit_myr": 30},
}

ANALYSIS_FOCUS = "我们是马来西亚 iGaming 运营商，旗下有 sureWin、maxwin、8win。"

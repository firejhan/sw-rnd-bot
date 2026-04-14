import sys
import time
import anthropic
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

import config
import database as db
from agents.promo_agent import run_promo_check, scrape_with_playwright
from agents.ad_agent import run_ad_check
from delivery.telegram_bot import send_telegram, format_alert_message


def summarize_promos(name, raw):
    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": f"""This is the promotions page of {name}:

{raw[:2500]}

List all promotions found. Format:

*{name}*
- Promo name | main condition (turnover / max bonus / min deposit)
- Promo name | main condition

Rules: one line per promo, no analysis, no recommendations. If nothing found write: No promotions detected."""}]
        )
        return msg.content[0].text
    except Exception as e:
        return f"*{name}*\nError: {e}"


def send_full_report():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    send_telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID,
        f"*Promo Intel Report*\n{now}\n{len(config.COMPETITORS)} platforms\n{'─'*22}")
    time.sleep(1)

    for platform in config.COMPETITORS:
        name = platform["name"]
        url  = platform["promo_url"]
        db.log("info", f"Scraping {name}...")
        raw     = scrape_with_playwright(url)
        summary = summarize_promos(name, raw)
        send_telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID, summary)
        time.sleep(2)

    send_telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID, "Report complete.")


def task_check_promos():
    db.log("info", "=== promo check ===")
    try:
        results = run_promo_check(config.COMPETITORS)
        for r in results:
            if r.get("changed"):
                alert = format_alert_message(r["competitor"], "promo", "Promo page updated", r.get("severity","high"))
                send_telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID, alert)
    except Exception as e:
        db.log("error", f"promo check error: {e}")


def task_daily_report():
    db.log("info", "=== daily report ===")
    try:
        send_full_report()
    except Exception as e:
        db.log("error", f"daily report error: {e}")
        send_telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID, f"Report error: {e}")


def start_scheduler():
    scheduler = BlockingScheduler(timezone="Asia/Kuala_Lumpur")
    scheduler.add_job(task_check_promos, IntervalTrigger(hours=config.CHECK_INTERVAL_HOURS), id="promo_check", replace_existing=True)
    scheduler.add_job(task_daily_report, CronTrigger(hour=config.DAILY_REPORT_HOUR, minute=config.DAILY_REPORT_MINUTE), id="daily_report", replace_existing=True)

    send_telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID,
        f"System started\nPlatforms: {len(config.COMPETITORS)}\nCheck every {config.CHECK_INTERVAL_HOURS}h\nDaily report at {config.DAILY_REPORT_HOUR:02d}:00")

    db.log("info", "Running initial full report...")
    send_full_report()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Stopped.")


if __name__ == "__main__":
    db.init_db()
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        send_full_report()
    else:
        start_scheduler()

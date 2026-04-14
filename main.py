import sys
import time
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

import config
import database as db
from agents.promo_agent import run_promo_check
from agents.ad_agent import run_ad_check
from agents.analysis_agent import analyze_changes, generate_no_change_summary
from delivery.telegram_bot import send_telegram, format_daily_report, format_alert_message


def task_check_promos():
    db.log("info", "=== promo check start ===")
    try:
        results = run_promo_check(config.COMPETITORS)
        for r in results:
            if r.get("changed") and r.get("severity") == "urgent":
                alert_msg = format_alert_message(
                    competitor=r["competitor"],
                    change_type="promo",
                    summary="Promo page major change: " + ", ".join(r.get("keywords", [])[:5]),
                    severity="urgent",
                )
                send_telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID, alert_msg)
    except Exception as e:
        db.log("error", f"promo check failed: {e}")


def task_check_ads():
    if not config.FB_ACCESS_TOKEN:
        return
    db.log("info", "=== ad check start ===")
    try:
        run_ad_check(getattr(config, 'FB_AD_KEYWORDS', []), config.FB_ACCESS_TOKEN)
    except Exception as e:
        db.log("error", f"ad check failed: {e}")


def task_daily_report():
    db.log("info", "=== daily report start ===")
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        changes = db.get_unreported_changes()
        if changes:
            analysis = analyze_changes(
                changes=changes,
                our_brands={},
                analysis_focus="",
                anthropic_api_key=config.ANTHROPIC_API_KEY,
            )
        else:
            analysis = generate_no_change_summary()

        report = format_daily_report(
            analysis=analysis,
            changes=changes,
            competitor_count=len(config.COMPETITORS),
        )
        db.save_daily_report(today, report)
        ok = send_telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID, report)
        if ok:
            db.mark_report_sent(today)
            if changes:
                db.mark_changes_reported([c["id"] for c in changes])
            db.log("info", "daily report sent ok")
    except Exception as e:
        db.log("error", f"daily report failed: {e}")
        send_telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID, f"Report error: {str(e)[:200]}")


def run_once():
    print("Running full check now...")
    task_check_promos()
    task_check_ads()
    task_daily_report()
    print("Done.")


def start_scheduler():
    scheduler = BlockingScheduler(timezone="Asia/Kuala_Lumpur")

    scheduler.add_job(task_check_promos, IntervalTrigger(hours=config.CHECK_INTERVAL_HOURS), id="promo_check", replace_existing=True)
    scheduler.add_job(task_daily_report, CronTrigger(hour=config.DAILY_REPORT_HOUR, minute=config.DAILY_REPORT_MINUTE), id="daily_report", replace_existing=True)
    scheduler.add_job(task_check_ads, CronTrigger(hour=(config.DAILY_REPORT_HOUR + 1) % 24, minute=0), id="ad_check", replace_existing=True)

    print("=== Competitor Intel System Started ===")
    print(f"Platforms: {len(config.COMPETITORS)}")
    print(f"Check interval: every {config.CHECK_INTERVAL_HOURS} hours")
    print(f"Daily report: {config.DAILY_REPORT_HOUR:02d}:{config.DAILY_REPORT_MINUTE:02d}")

    msg = (
        "System started\n\n"
        f"Platforms: {len(config.COMPETITORS)}\n"
        f"Check every {config.CHECK_INTERVAL_HOURS} hours\n"
        f"Daily report at {config.DAILY_REPORT_HOUR:02d}:00"
    )
    send_telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID, msg)

    task_check_promos()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Stopped.")


if __name__ == "__main__":
    db.init_db()
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        run_once()
    else:
        start_scheduler()

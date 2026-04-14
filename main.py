import sys
import time
import anthropic
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

import config
import database as db
from agents.promo_agent import scrape_with_playwright
from agents.ad_agent import run_ad_check
from delivery.telegram_bot import send_telegram


def summarize_promos(name, raw):
    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": f"""This is the promotions page of {name}:

{raw[:2500]}

List all promotions. Format:
*{name}*
- Promo name | main condition

Format each promo exactly like this:

- 🎁 Promo Name
  💰 Bonus: e.g. 100% up to MYR 500
  🔄 Turnover: e.g. x20
  💵 Min Deposit: e.g. MYR 30
  📋 How to join: e.g. Deposit and bonus auto-credited
  ⏰ Validity: e.g. Daily / One-time / Ongoing

Only include fields that are mentioned. Skip fields with no info.
No analysis, no recommendations."""}]
        )
        return msg.content[0].text
    except Exception as e:
        return f"*{name}*\nError: {e}"


def get_promo_changes(name, old_text, new_text):
    """Use Claude to compare old vs new and return only what changed"""
    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": f"""Compare these two versions of {name} promotions page.

BEFORE:
{old_text[:1500]}

AFTER:
{new_text[:1500]}

List ONLY what changed. Format:

*{name} - Promo Update* 🔔

➕ New promotions:
- promo name | condition

❌ Removed promotions:
- promo name

✏️ Changed promotions:
- promo name | what changed

If nothing changed write: No changes detected.
If you cannot compare properly write: Page updated - manual review needed."""}]
        )
        return msg.content[0].text
    except Exception as e:
        return f"*{name}*\nError comparing: {e}"


def task_check_promos():
    db.log("info", "=== Checking promos for changes ===")
    changes_found = []

    for platform in config.COMPETITORS:
        name = platform["name"]
        url  = platform["promo_url"]

        db.log("info", f"Checking {name}...")
        new_text = scrape_with_playwright(url)

        if not new_text or "Failed" in new_text[:20]:
            db.log("warn", f"{name}: fetch failed")
            continue

        last = db.get_last_snapshot(name)

        if last is None:
            # First time - save baseline, no report
            db.save_snapshot(name, url, new_text)
            db.log("info", f"{name}: baseline saved")
            continue

        from database import hash_content
        if last["content_hash"] == hash_content(new_text):
            db.log("info", f"{name}: no change")
            continue

        # Change detected
        db.log("info", f"{name}: CHANGE DETECTED")
        change_summary = get_promo_changes(name, last["content"], new_text)
        db.save_snapshot(name, url, new_text)
        db.record_change(
            competitor=name,
            change_type="promo",
            old_content=last["content"][:2000],
            new_content=new_text[:2000],
            summary=change_summary,
            severity="high"
        )
        changes_found.append((name, change_summary))
        time.sleep(2)

    if changes_found:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        send_telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID,
            f"🔔 *Promo Changes Detected*\n{now}\n{'─'*22}")
        for name, summary in changes_found:
            send_telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID, summary)
            time.sleep(1)
    else:
        db.log("info", "No changes found across all platforms")


def send_full_report():
    """Send full promo report for all platforms"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    send_telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID,
        f"📊 *Daily Promo Report*\n{now}\n{len(config.COMPETITORS)} platforms\n{'─'*22}")
    time.sleep(1)

    for platform in config.COMPETITORS:
        name = platform["name"]
        url  = platform["promo_url"]
        db.log("info", f"Scraping {name}...")
        raw     = scrape_with_playwright(url)
        summary = summarize_promos(name, raw)
        send_telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID, summary)
        time.sleep(2)

    send_telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID,
        "✅ Daily report complete.")


def start_scheduler():
    scheduler = BlockingScheduler(timezone="Asia/Kuala_Lumpur")

    # Check for changes every 6 hours
    scheduler.add_job(task_check_promos,
        IntervalTrigger(hours=config.CHECK_INTERVAL_HOURS),
        id="promo_check", replace_existing=True)

    # Full report every day at 8am
    scheduler.add_job(send_full_report,
        CronTrigger(hour=config.DAILY_REPORT_HOUR, minute=config.DAILY_REPORT_MINUTE),
        id="daily_report", replace_existing=True)

    send_telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID,
        f"✅ System started\n"
        f"📡 Platforms: {len(config.COMPETITORS)}\n"
        f"🔔 Change alerts: every {config.CHECK_INTERVAL_HOURS}h\n"
        f"📬 Full report: daily at {config.DAILY_REPORT_HOUR:02d}:00")

    # Run initial check on startup
    db.log("info", "Running startup full report...")
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

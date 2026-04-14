"""
main.py — 系统总指挥 (Orchestrator)
负责：
  1. 定时触发所有 Agent
  2. 协调数据流动：采集 → 分析 → 推送
  3. 记录运行日志
  4. 处理错误和重试

运行方式：
  python main.py          ← 启动调度器（24小时持续运行）
  python main.py --now    ← 立刻执行一次完整的检查（测试用）
"""

import sys
import time
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# ─── 导入配置 ──────────────────────────────────────────────────
import config

# ─── 导入所有 Agent 和模块 ────────────────────────────────────
import database as db
from agents.promo_agent    import run_promo_check
from agents.ad_agent       import check_new_ads
from agents.analysis_agent import analyze_changes, generate_no_change_summary
from delivery.telegram_bot import (
    send_telegram,
    format_daily_report,
    format_alert_message,
)


# ══════════════════════════════════════════════════════════════
#  核心任务 1：促销检查（每几小时运行一次）
# ══════════════════════════════════════════════════════════════
def task_check_promos():
    """
    检查所有竞品的促销页面变化。
    发现 urgent 级别变化时，立刻推送预警到 Telegram。
    """
    db.log("info", "=== 开始促销检查任务 ===")
    try:
        results = run_promo_check(config.COMPETITORS)

        # 对 urgent 级别变化立刻推送预警
        for r in results:
            if r.get("changed") and r.get("severity") == "urgent":
                alert_msg = format_alert_message(
                    competitor  = r["competitor"],
                    change_type = "promo",
                    summary     = f"促销页面重大变动！发现关键词: {', '.join(r.get('keywords', [])[:5])}",
                    severity    = "urgent",
                )
                send_telegram(config.TELEGRAM_BOT_TOKEN,
                              config.TELEGRAM_CHAT_ID,
                              alert_msg)
                db.log("info", f"已推送 {r['competitor']} 的紧急预警")

    except Exception as e:
        db.log("error", f"促销检查任务失败: {e}")


# ══════════════════════════════════════════════════════════════
#  核心任务 2：Facebook 广告检查（每天运行）
# ══════════════════════════════════════════════════════════════
def task_check_ads():
    """
    检查竞品 Facebook 广告库，记录新广告。
    """
    if not config.FB_ACCESS_TOKEN:
        return  # 未配置 FB token，跳过

    db.log("info", "=== 开始广告检查任务 ===")
    try:
        known_ad_ids = set()  # 可以从数据库读取已知广告ID
        new_ads = check_new_ads(
            config.COMPETITORS,
            config.FB_ACCESS_TOKEN,
            known_ad_ids,
        )
        if new_ads:
            db.log("info", f"发现 {len(new_ads)} 条新广告")
    except Exception as e:
        db.log("error", f"广告检查任务失败: {e}")


# ══════════════════════════════════════════════════════════════
#  核心任务 3：生成并推送每日情报日报
# ══════════════════════════════════════════════════════════════
def task_daily_report():
    """
    每天定时运行：
    1. 获取所有未报告的变化
    2. 用 Claude 生成分析报告
    3. 推送到 Telegram
    4. 标记已报告
    """
    db.log("info", "=== 开始生成每日情报日报 ===")
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        # 获取待分析的变化
        changes = db.get_unreported_changes()
        db.log("info", f"今日待分析变化: {len(changes)} 条")

        # 生成分析
        if changes:
            analysis = analyze_changes(
                changes        = changes,
                our_brands     = config.OUR_BRANDS,
                analysis_focus = config.ANALYSIS_FOCUS,
                anthropic_api_key = config.ANTHROPIC_API_KEY,
            )
        else:
            analysis = generate_no_change_summary()

        # 格式化报告
        report = format_daily_report(
            analysis          = analysis,
            changes           = changes,
            competitor_count  = len(config.COMPETITORS),
        )

        # 保存到数据库
        db.save_daily_report(today, report)

        # 推送到 Telegram
        ok = send_telegram(config.TELEGRAM_BOT_TOKEN,
                           config.TELEGRAM_CHAT_ID,
                           report)
        if ok:
            db.mark_report_sent(today)
            if changes:
                db.mark_changes_reported([c["id"] for c in changes])
            db.log("info", "每日日报推送成功 ✅")
        else:
            db.log("error", "每日日报推送失败")

    except Exception as e:
        db.log("error", f"每日日报任务失败: {e}")
        # 失败时发一条简短的错误通知
        send_telegram(
            config.TELEGRAM_BOT_TOKEN,
            config.TELEGRAM_CHAT_ID,
            f"⚠️ 竞品情报系统报告生成失败\n错误: {str(e)[:200]}"
        )


# ══════════════════════════════════════════════════════════════
#  立刻运行一次（测试用）
# ══════════════════════════════════════════════════════════════
def run_once():
    """
    用 python main.py --now 触发，立刻执行完整流程
    """
    print("\n🚀 立刻执行完整情报检查...\n")
    print("步骤 1/3: 检查促销页面...")
    task_check_promos()

    print("步骤 2/3: 检查广告...")
    task_check_ads()

    print("步骤 3/3: 生成日报并推送...")
    task_daily_report()

    print("\n✅ 完整检查完成！请查看你的 Telegram。\n")


# ══════════════════════════════════════════════════════════════
#  调度器（Orchestrator）— 定时触发所有 Agent
# ══════════════════════════════════════════════════════════════
def start_scheduler():
    """
    启动定时调度器：
    - 每 N 小时  → 促销页面检查
    - 每天早上   → 生成并推送日报
    - 每天早上+1 → 广告检查
    """
    scheduler = BlockingScheduler(timezone="Asia/Kuala_Lumpur")

    # ── 促销检查：每隔 N 小时 ──────────────────────────────────
    scheduler.add_job(
        task_check_promos,
        trigger = IntervalTrigger(hours=config.CHECK_INTERVAL_HOURS),
        id      = "promo_check",
        name    = "促销页面检查",
        replace_existing = True,
    )

    # ── 每日日报：每天早上定时 ─────────────────────────────────
    scheduler.add_job(
        task_daily_report,
        trigger = CronTrigger(
            hour   = config.DAILY_REPORT_HOUR,
            minute = config.DAILY_REPORT_MINUTE,
        ),
        id   = "daily_report",
        name = "每日情报日报",
        replace_existing = True,
    )

    # ── 广告检查：每天早上晚1小时 ─────────────────────────────
    scheduler.add_job(
        task_check_ads,
        trigger = CronTrigger(
            hour   = (config.DAILY_REPORT_HOUR + 1) % 24,
            minute = config.DAILY_REPORT_MINUTE,
        ),
        id   = "ad_check",
        name = "广告库检查",
        replace_existing = True,
    )

    print("\n" + "═" * 50)
    print("  🤖 竞品情报系统 已启动")
    print("═" * 50)
    print(f"  📡 监控竞品: {len(config.COMPETITORS)} 个")
    print(f"  ⏱️  促销检查: 每 {config.CHECK_INTERVAL_HOURS} 小时")
    print(f"  📬 每日日报: 每天 {config.DAILY_REPORT_HOUR:02d}:{config.DAILY_REPORT_MINUTE:02d}")
    print(f"  🇲🇾 时区: Asia/Kuala_Lumpur")
    print("═" * 50)
    print("  按 Ctrl+C 停止\n")

    # 启动时立刻做一次促销检查（不等第一个计时器到期）
    print("🔍 启动时先做一次初始检查...")
    task_check_promos()

    from delivery.telegram_bot import send_telegram
    send_telegram(
        config.TELEGRAM_BOT_TOKEN,
        config.TELEGRAM_CHAT_ID,
        '✅ *竞品情报系统已启动*

📡 监控平台: ' + str(len(config.COMPETITORS)) + ' 个
⏱️ 每 ' + str(config.CHECK_INTERVAL_HOURS) + ' 小时检查一次
📬 每天 ' + str(config.DAILY_REPORT_HOUR) + ':00 发日报

系统运行中，有变化会自动通知你。'
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n\n⛔ 系统已停止\n")


# ══════════════════════════════════════════════════════════════
#  程序入口
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # 初始化数据库（如果是第一次运行）
    db.init_db()

    # 检查参数
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        # 立刻运行一次（测试模式）
        run_once()
    else:
        # 正常模式：启动调度器，持续运行
        start_scheduler()

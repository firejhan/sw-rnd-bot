"""
delivery/telegram_bot.py — Telegram 推送模块
把情报报告发送到你的 Telegram
"""

import requests
from datetime import datetime
from database import log


def send_telegram(bot_token: str, chat_id: str, text: str,
                  parse_mode: str = "Markdown") -> bool:
    """
    发送 Telegram 消息
    返回 True = 成功，False = 失败
    """
    if not bot_token or not chat_id:
        log("error", "Telegram token 或 chat_id 未配置")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # Telegram 单条消息最多 4096 字符，超长就分段发
    chunks = split_message(text, max_len=4000)

    success = True
    for chunk in chunks:
        try:
            resp = requests.post(url, json={
                "chat_id":    chat_id,
                "text":       chunk,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }, timeout=15)

            if not resp.ok:
                log("warn", f"Telegram 发送失败: {resp.text}")
                # 如果 Markdown 格式有问题，改用纯文本重试
                resp2 = requests.post(url, json={
                    "chat_id": chat_id,
                    "text":    chunk,
                }, timeout=15)
                success = resp2.ok

        except Exception as e:
            log("error", f"Telegram 发送异常: {e}")
            success = False

    return success


def split_message(text: str, max_len: int = 4000) -> list:
    """把长消息拆分成多段"""
    if len(text) <= max_len:
        return [text]
    parts = []
    while text:
        parts.append(text[:max_len])
        text = text[max_len:]
    return parts


def format_daily_report(analysis: str, changes: list,
                         competitor_count: int) -> str:
    """
    格式化每日情报报告
    """
    today    = datetime.now().strftime("%Y-%m-%d")
    weekday  = ["周一","周二","周三","周四","周五","周六","周日"][datetime.now().weekday()]
    now_time = datetime.now().strftime("%H:%M")

    changed_names = list(set(c["competitor"] for c in changes))
    urgent_count  = sum(1 for c in changes if c.get("severity") == "urgent")
    high_count    = sum(1 for c in changes if c.get("severity") == "high")

    # 严重程度表情
    if urgent_count > 0:
        alert_emoji = "🚨"
    elif high_count > 0:
        alert_emoji = "⚠️"
    else:
        alert_emoji = "📊"

    header = f"""{alert_emoji} *竞品情报日报 | {today} {weekday}*
⏰ 生成时间: {now_time}
📡 监控竞品: {competitor_count} 个
🔄 今日变化: {len(changes)} 条"""

    if changed_names:
        header += f"\n📌 有变动的竞品: {', '.join(changed_names)}"

    if urgent_count > 0:
        header += f"\n🚨 紧急预警: {urgent_count} 条"

    separator = "\n" + "─" * 30 + "\n"

    return header + separator + analysis


def format_alert_message(competitor: str, change_type: str,
                          summary: str, severity: str) -> str:
    """
    格式化即时预警消息（当检测到 urgent 级别变化时立刻推送）
    """
    emoji_map = {
        "urgent": "🚨",
        "high":   "⚠️",
        "normal": "📌",
    }
    type_map = {
        "promo": "促销变动",
        "ad":    "新广告上线",
        "social":"社媒动态",
        "seo":   "SEO变化",
    }
    emoji     = emoji_map.get(severity, "📌")
    type_name = type_map.get(change_type, change_type)
    now       = datetime.now().strftime("%H:%M")

    return f"""{emoji} *即时预警 [{now}]*
竞品: *{competitor}*
类型: {type_name}
重要程度: {severity.upper()}

{summary}

_(由竞品情报系统自动检测)_"""

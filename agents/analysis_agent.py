"""
analysis_agent.py — 只整理促销活动列表，不做分析
"""
import anthropic
from database import log


def summarize_platform_promos(platform_name: str, raw_text: str, api_key: str) -> str:
    """
    把抓取到的原始内容，整理成清晰的活动列表
    """
    if not raw_text or "抓取失败" in raw_text or "无法连接" in raw_text:
        return f"📊 *{platform_name}*\n⚠️ 页面无法读取\n"

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""以下是 {platform_name} 促销页面的内容：

{raw_text[:3000]}

请把上面的内容整理成促销活动列表。

格式要求：
📊 *{platform_name}*

💰 存款优惠
- 活动名称 | 基本条件（如有）

🎾 体育优惠
- 活动名称 | 基本条件（如有）

🃏 真人赌场
- 活动名称 | 基本条件（如有）

🎰 老虎机
- 活动名称 | 基本条件（如有）

🎁 其他优惠
- 活动名称 | 基本条件（如有）

规则：
- 只列有的分类，没有的分类不要写
- 每个活动一行，用 • 开头
- 只写活动名称和最基本的条件（流水要求、最高奖励）
- 不要写建议、不要做分析、不要评论
- 如果内容不清楚就写活动名称就好
"""

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text

    except Exception as e:
        log("error", f"Claude 整理失败 [{platform_name}]: {e}")
        return f"📊 *{platform_name}*\n⚠️ 整理失败: {str(e)[:50]}\n"


def build_daily_header(total_platforms: int) -> str:
    from datetime import datetime
    now = datetime.now()
    weekdays = ["周一","周二","周三","周四","周五","周六","周日"]
    return (
        f"🗓 *促销情报日报*\n"
        f"{now.strftime('%Y-%m-%d')} {weekdays[now.weekday()]} "
        f"{now.strftime('%H:%M')}\n"
        f"共 {total_platforms} 个平台\n"
        f"{'─' * 25}"
    )

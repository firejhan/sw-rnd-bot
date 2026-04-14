"""
agents/analysis_agent.py — Claude 分析 Agent
把原始抓取数据变成有价值的情报分析
"""

import anthropic
from database import get_unreported_changes, log


def build_analysis_prompt(changes: list, our_brands: dict, analysis_focus: str) -> str:
    """
    构建分析提示词
    """
    changes_text = ""
    for i, ch in enumerate(changes, 1):
        changes_text += f"""
【变化 {i}】竞品: {ch['competitor']} | 类型: {ch['change_type']} | 重要程度: {ch['severity']}
发现时间: {ch['detected_at']}
变化摘要: {ch['summary']}

旧内容（部分）:
{ch.get('old_content', '无')[:400]}

新内容（部分）:
{ch.get('new_content', '无')[:400]}
---"""

    our_brands_text = ""
    for brand, info in our_brands.items():
        our_brands_text += f"• {brand}: {info}\n"

    return f"""你是一个专业的马来西亚/新加坡 iGaming 竞品情报分析师。

{analysis_focus}

我们的品牌现状：
{our_brands_text}

今天检测到的竞品变化如下：
{changes_text}

请用中文生成一份简洁有力的情报分析，包含以下部分：

⚠️ **今日预警**（如果有urgent/high级别变化，必须重点说明）
列出所有重要变化和可能对我们造成的影响

📊 **促销动态**
每个竞品的具体变化，用简短的一两句说清楚

🎯 **机会与威胁**
- 威胁：哪些竞品动作可能抢走我们用户？
- 机会：竞品有什么弱点或空白我们可以利用？

💡 **立刻可以做的3件事**
具体的行动建议，针对我们的品牌（sureWin/maxwin/8win/winX）

分析要实用、直接、有结论，不要废话。"""


def analyze_changes(changes: list, our_brands: dict, analysis_focus: str,
                    anthropic_api_key: str) -> str:
    """
    用 Claude 分析今日所有变化
    """
    if not changes:
        return "今日无新变化，暂无需要分析的内容。"

    client = anthropic.Anthropic(api_key=anthropic_api_key)

    prompt = build_analysis_prompt(changes, our_brands, analysis_focus)

    log("info", f"正在用 Claude 分析 {len(changes)} 条变化...")

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        analysis = message.content[0].text
        log("info", "Claude 分析完成")
        return analysis

    except Exception as e:
        log("error", f"Claude 分析失败: {e}")
        return f"⚠️ 分析生成失败: {e}\n\n原始变化记录:\n" + "\n".join(
            f"• {c['competitor']}: {c['summary']}" for c in changes
        )


def generate_no_change_summary() -> str:
    """
    今日无变化时的报告内容
    """
    return "✅ 今日所有竞品促销页面均无明显变化，市场稳定。"

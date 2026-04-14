"""
agents/promo_agent.py — 促销页面监控 Agent
每隔几小时抓取竞品促销页面，检测内容是否有变化
"""

import time
import requests
from bs4 import BeautifulSoup
from database import get_last_snapshot, save_snapshot, record_change, hash_content, log


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_page_text(url: str) -> str | None:
    """
    抓取网页，提取纯文字内容（去掉 HTML 标签、广告脚本等）
    返回 None 表示抓取失败
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 删除不需要的标签
        for tag in soup(["script", "style", "nav", "footer", "header", "iframe"]):
            tag.decompose()

        # 提取关键文字
        text = soup.get_text(separator="\n", strip=True)

        # 只保留有实质内容的行（去掉空行、太短的行）
        lines = [line for line in text.splitlines() if len(line.strip()) > 10]
        cleaned = "\n".join(lines[:200])  # 最多保留200行，避免太长

        return cleaned

    except requests.exceptions.ConnectionError:
        log("warn", f"无法连接到 {url}（可能被封IP或网站变更）")
        return None
    except requests.exceptions.Timeout:
        log("warn", f"抓取超时: {url}")
        return None
    except Exception as e:
        log("error", f"抓取失败 {url}: {e}")
        return None


def detect_promo_keywords(text: str) -> list:
    """
    检测促销关键词，帮助判断变化的重要性
    发现越多关键词 = 变化越重要
    """
    keywords = [
        # 优惠力度词
        "100%", "150%", "200%", "300%",
        "首存", "新会员", "欢迎奖励", "welcome bonus",
        "free credit", "免费", "无需存款", "no deposit",
        # 活动类型词
        "限时", "今日", "特别", "exclusive", "vip",
        "现金回馈", "cashback", "返水", "rebate",
        # 数字金额词（MYR/RM）
        "RM", "MYR", "rm100", "rm200", "rm500",
    ]
    found = []
    text_lower = text.lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            found.append(kw)
    return found


def assess_severity(old_text: str, new_text: str) -> str:
    """
    判断变化的严重程度：
    - urgent: 可能影响我们用户流失
    - high:   值得立刻关注
    - normal: 小变动，记录即可
    """
    new_lower = new_text.lower()

    urgent_signals = ["200%", "300%", "no deposit", "免费", "0存款", "free"]
    high_signals   = ["150%", "100%首存", "限时", "exclusive", "cashback", "返水"]

    for signal in urgent_signals:
        if signal.lower() in new_lower:
            return "urgent"
    for signal in high_signals:
        if signal.lower() in new_lower:
            return "high"
    return "normal"


def check_competitor_promo(competitor: dict) -> dict:
    """
    检查单个竞品的促销页面是否有变化
    返回结果字典
    """
    name = competitor["name"]
    url  = competitor["promo_url"]

    log("info", f"检查 {name} 促销页面...")
    current_text = fetch_page_text(url)

    if current_text is None:
        return {"competitor": name, "status": "fetch_failed", "changed": False}

    current_hash = hash_content(current_text)
    last = get_last_snapshot(name)

    # 第一次运行，没有历史数据
    if last is None:
        save_snapshot(name, url, current_text)
        log("info", f"{name}: 首次记录基准快照")
        return {"competitor": name, "status": "baseline_saved", "changed": False}

    # 内容没有变化
    if last["content_hash"] == current_hash:
        log("info", f"{name}: 无变化")
        return {"competitor": name, "status": "no_change", "changed": False}

    # ✅ 检测到变化！
    old_text  = last["content"]
    severity  = assess_severity(old_text, current_text)
    keywords  = detect_promo_keywords(current_text)

    # 保存新快照
    save_snapshot(name, url, current_text)

    # 记录变化
    record_change(
        competitor  = name,
        change_type = "promo",
        old_content = old_text[:2000],    # 截断避免数据库太大
        new_content = current_text[:2000],
        summary     = f"促销页面有更新，发现关键词: {', '.join(keywords[:5]) if keywords else '无特殊关键词'}",
        severity    = severity
    )

    log("info", f"🔔 {name}: 检测到{severity}级促销变化！关键词: {keywords}")
    return {
        "competitor": name,
        "status":     "changed",
        "changed":    True,
        "severity":   severity,
        "keywords":   keywords,
        "old_text":   old_text[:500],
        "new_text":   current_text[:500],
    }


def run_promo_check(competitors: list) -> list:
    """
    对所有竞品运行促销检查
    返回所有变化的列表
    """
    log("info", f"开始促销监控，共 {len(competitors)} 个竞品")
    results = []

    for comp in competitors:
        result = check_competitor_promo(comp)
        results.append(result)
        time.sleep(2)  # 礼貌间隔，避免被反爬

    changed = [r for r in results if r.get("changed")]
    log("info", f"促销检查完成：{len(changed)} 个竞品有变化")
    return results

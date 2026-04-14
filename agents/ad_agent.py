"""
agents/ad_agent.py — Facebook 广告监控 Agent
通过 FB Ad Library API 监控竞品正在投放的广告
"""

import requests
from database import log, record_change


FB_ADS_API = "https://graph.facebook.com/v19.0/ads_archive"


def fetch_competitor_ads(fb_page_id: str, fb_access_token: str,
                         competitor_name: str) -> list:
    """
    从 Facebook Ad Library 获取竞品广告
    需要 FB Access Token（在 https://developers.facebook.com/ 申请）
    """
    if not fb_access_token or not fb_page_id:
        return []

    try:
        params = {
            "access_token":      fb_access_token,
            "ad_type":           "ALL",
            "ad_active_status":  "ACTIVE",
            "search_page_ids":   fb_page_id,
            "fields":            "id,ad_creative_body,ad_creative_link_caption,ad_delivery_start_time",
            "limit":             20,
        }
        resp = requests.get(FB_ADS_API, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        ads  = data.get("data", [])
        log("info", f"{competitor_name}: 获取到 {len(ads)} 条广告")
        return ads

    except Exception as e:
        log("warn", f"{competitor_name} 广告获取失败: {e}")
        return []


def check_new_ads(competitors: list, fb_access_token: str,
                  known_ad_ids: set) -> list:
    """
    检查所有竞品的新广告
    返回新发现的广告列表
    """
    if not fb_access_token:
        log("info", "FB_ACCESS_TOKEN 未配置，跳过广告监控")
        return []

    new_ads = []
    for comp in competitors:
        if not comp.get("fb_page_id"):
            continue

        ads = fetch_competitor_ads(
            comp["fb_page_id"], fb_access_token, comp["name"]
        )
        for ad in ads:
            ad_id = ad.get("id", "")
            if ad_id and ad_id not in known_ad_ids:
                ad["competitor"] = comp["name"]
                new_ads.append(ad)
                record_change(
                    competitor  = comp["name"],
                    change_type = "ad",
                    old_content = "",
                    new_content = ad.get("ad_creative_body", "（无文案）"),
                    summary     = f"发现新广告: {ad.get('ad_creative_body', '')[:100]}",
                    severity    = "high"
                )

    return new_ads


def get_ad_library_url(fb_page_id: str, country: str = "MY") -> str:
    """
    生成 Facebook Ad Library 的查看链接（无需API，直接在浏览器看）
    """
    return (
        f"https://www.facebook.com/ads/library/"
        f"?active_status=active&ad_type=all&country={country}"
        f"&search_type=page&view_all_page_id={fb_page_id}"
    )

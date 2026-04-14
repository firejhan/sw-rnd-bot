import requests
import os
from database import log

FB_ADS_API = "https://graph.facebook.com/v19.0/ads_archive"

def run_ad_check(keywords, fb_access_token):
    if not fb_access_token or not keywords:
        log("info", "FB_ACCESS_TOKEN not set, skipping ad check")
        return {}

    results = {}
    seen_ids = set()

    for keyword in keywords:
        try:
            params = {
                "access_token":         fb_access_token,
                "ad_type":              "ALL",
                "ad_active_status":     "ACTIVE",
                "search_terms":         keyword,
                "ad_reached_countries": "MY",
                "fields":               "id,page_name,ad_creative_body,ad_creative_link_title,ad_delivery_start_time,ad_snapshot_url",
                "limit":                10,
            }
            resp = requests.get(FB_ADS_API, params=params, timeout=15)
            data = resp.json()

            if "error" in data:
                log("warn", f"FB API error for '{keyword}': {data['error'].get('message','')}")
                continue

            ads = data.get("data", [])
            new_ads = []
            for ad in ads:
                ad_id = ad.get("id", "")
                if ad_id and ad_id not in seen_ids:
                    seen_ids.add(ad_id)
                    new_ads.append(ad)

            if new_ads:
                results[keyword] = new_ads
                log("info", f"Keyword '{keyword}': {len(new_ads)} ads found")

        except Exception as e:
            log("warn", f"Ad check failed for '{keyword}': {e}")

    total = sum(len(v) for v in results.values())
    log("info", f"Ad check done: {total} ads across {len(results)} keywords")
    return results

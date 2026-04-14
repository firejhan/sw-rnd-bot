import requests
from database import log, record_change

FB_ADS_API = "https://graph.facebook.com/v19.0/ads_archive"

def run_ad_check(keywords, fb_access_token):
    if not fb_access_token or not keywords:
        return {}
    results = {}
    seen_ids = set()
    for keyword in keywords:
        try:
            params = {
                "access_token": fb_access_token,
                "ad_type": "ALL",
                "ad_active_status": "ACTIVE",
                "search_terms": keyword,
                "ad_reached_countries": "MY",
                "fields": "id,page_name,ad_creative_body,ad_creative_link_title,ad_delivery_start_time,ad_snapshot_url",
                "limit": 10,
            }
            resp = requests.get(FB_ADS_API, params=params, timeout=15)
            ads = resp.json().get("data", [])
            new_ads = []
            for ad in ads:
                ad_id = ad.get("id", "")
                if ad_id and ad_id not in seen_ids:
                    seen_ids.add(ad_id)
                    new_ads.append(ad)
                    record_change(
                        competitor=ad.get("page_name", keyword),
                        change_type="ad",
                        old_content="",
                        new_content=ad.get("ad_creative_body", "")[:500],
                        summary="New ad: " + ad.get("ad_creative_link_title", "")[:100],
                        severity="high"
                    )
            if new_ads:
                results[keyword] = new_ads
        except Exception as e:
            log("warn", f"Ad check failed [{keyword}]: {e}")
    return results

import time
from database import get_last_snapshot, save_snapshot, record_change, hash_content, log

def scrape_with_playwright(url):
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
                locale="en-MY",
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=45000)
            time.sleep(3)
            for _ in range(8):
                page.evaluate("window.scrollBy(0, 600)")
                time.sleep(0.8)
            text = page.inner_text("body")
            browser.close()
            lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 8]
            return "\n".join(lines[:500])
    except Exception as e:
        log("warn", f"Playwright failed for {url}: {e}")
        return f"Failed to load: {e}"

def check_competitor_promo(competitor):
    name = competitor["name"]
    url  = competitor["promo_url"]
    log("info", f"Scraping {name}...")
    current_text = scrape_with_playwright(url)
    if not current_text or len(current_text) < 100:
        return {"competitor": name, "status": "fetch_failed", "changed": False, "content": "Unable to fetch"}
    current_hash = hash_content(current_text)
    last = get_last_snapshot(name)
    if last is None:
        save_snapshot(name, url, current_text)
        return {"competitor": name, "status": "baseline_saved", "changed": False, "content": current_text}
    if last["content_hash"] == current_hash:
        return {"competitor": name, "status": "no_change", "changed": False, "content": current_text}
    save_snapshot(name, url, current_text)
    record_change(competitor=name, change_type="promo", old_content=last["content"][:2000], new_content=current_text[:2000], summary="Promo page updated", severity="high")
    return {"competitor": name, "status": "changed", "changed": True, "content": current_text}

def run_promo_check(competitors):
    results = []
    for comp in competitors:
        result = check_competitor_promo(comp)
        results.append(result)
        time.sleep(2)
    return results

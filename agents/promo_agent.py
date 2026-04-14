import time
from database import get_last_snapshot, save_snapshot, record_change, hash_content, log

def scrape_with_playwright(url):
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"})
            page.goto(url, wait_until="networkidle", timeout=30000)
            # Scroll down to load all content
            for _ in range(5):
                page.evaluate("window.scrollBy(0, 800)")
                time.sleep(0.8)
            # Extract all visible text
            text = page.inner_text("body")
            browser.close()
            lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 8]
            return "\n".join(lines[:200])
    except Exception as e:
        log("warn", f"Playwright failed for {url}: {e}")
        return f"Failed to load: {e}"

def check_competitor_promo(competitor):
    name = competitor["name"]
    url  = competitor["promo_url"]
    log("info", f"Scraping {name}...")
    current_text = scrape_with_playwright(url)
    if not current_text or "Failed" in current_text[:20]:
        return {"competitor": name, "status": "fetch_failed", "changed": False, "content": current_text}
    current_hash = hash_content(current_text)
    last = get_last_snapshot(name)
    if last is None:
        save_snapshot(name, url, current_text)
        return {"competitor": name, "status": "baseline_saved", "changed": False, "content": current_text}
    if last["content_hash"] == current_hash:
        return {"competitor": name, "status": "no_change", "changed": False, "content": current_text}
    save_snapshot(name, url, current_text)
    record_change(competitor=name, change_type="promo", old_content=last["content"][:2000], new_content=current_text[:2000], summary=f"Promo page updated", severity="high")
    return {"competitor": name, "status": "changed", "changed": True, "content": current_text}

def run_promo_check(competitors):
    log("info", f"Starting promo check for {len(competitors)} platforms")
    results = []
    for comp in competitors:
        result = check_competitor_promo(comp)
        results.append(result)
        time.sleep(2)
    changed = [r for r in results if r.get("changed")]
    log("info", f"Promo check done: {len(changed)} changed")
    return results

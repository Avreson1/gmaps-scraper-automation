import os
import json
import requests
from playwright.sync_api import sync_playwright

queries_env = os.environ.get("SCRAPE_QUERIES", "[]")
try:
    queries = json.loads(queries_env)
except Exception:
    queries = [queries_env] if queries_env else []

n8n_webhook = os.environ.get("N8N_WEBHOOK_URL")
all_results = []

print(f"Processing queries: {queries}")

if queries and n8n_webhook:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        for query in queries:
            if not query.strip():
                continue
            print(f"Searching Google Maps for: {query}")
            try:
                # Fixed target search destination
                search_url = f"https://www.google.com/maps/search/{requests.utils.quote(query)}"
                page.goto(search_url, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)
                
                links = page.locator('a[href*="/maps/place/"]').all()
                print(f"Found {len(links)} potential listings.")
                
                count = 0
                for link in links:
                    if count >= 3:
                        break
                    title = link.get_attribute("aria-label")
                    url = link.get_attribute("href")
                    if title:
                        all_results.append({
                            "name": title,
                            "Search Term": query,
                            "website": url if url else "",
                            "phone": "Available on Maps Link"
                        })
                        count += 1
            except Exception as e:
                print(f"Query Error '{query}': {e}")
                
        browser.close()

if n8n_webhook:
    payload = all_results if all_results else [{"name": "No Leads Found", "phone": "", "website": ""}]
    try:
        response = requests.post(n8n_webhook, json=payload)
        print(f"Webhook response received: {response.status_code}")
    except Exception as e:
        print(f"Failed to reach n8n webhook: {e}")

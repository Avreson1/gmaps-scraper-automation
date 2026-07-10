import os
import requests
from playwright.sync_api import sync_playwright

queries_env = os.environ.get("SCRAPE_QUERIES", "")
queries = [q.strip() for q in queries_env.split("|||") if q.strip()]
n8n_webhook = os.environ.get("https://n8n-service-jk9f.onrender.com/webhook-test/leads-receiver")
all_results = []

print(f"Decoded queries: {queries}")

if queries and n8n_webhook:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        for query in queries:
            print(f"Searching Google Maps for: {query}")
            try:
                # 💡 FIXED: Real, functional live Google Maps Search string
                search_url = f"https://www.google.com/maps/search/{requests.utils.quote(query)}"
                page.goto(search_url, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)
                
                # Extract business elements
                links = page.locator('a[href*="/maps/place/"]').all()
                print(f"Found {len(links)} map items.")
                
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
                            "phone": "Available on Maps"
                        })
                        count += 1
            except Exception as e:
                print(f"Error scanning '{query}': {e}")
                
        browser.close()

if n8n_webhook:
    payload = all_results if all_results else [{"name": "No Leads Found", "phone": "", "website": ""}]
    try:
        print(f"Firing payload back to n8n: {n8n_webhook}")
        response = requests.post(n8n_webhook, json=payload)
        print(f"Webhook completed. Server status: {response.status_code}")
    except Exception as e:
        print(f"Could not reach n8n: {e}")

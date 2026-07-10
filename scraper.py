import os
import json
import requests
from playwright.sync_api import sync_playwright

# 1. Grab target queries passed from your n8n workflow
queries_env = os.environ.get("SCRAPE_QUERIES", "[]")
queries = json.loads(queries_env)
n8n_webhook = os.environ.get("N8N_WEBHOOK_URL")

all_results = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    for query in queries:
        print(f"Scraping: {query}")
        try:
            # Search Google Maps
            page.goto(f"https://www.google.com/maps/search/{query.replace(' ', '+')}")
            page.wait_for_timeout(5000) # Give it 5 seconds to load listings
            
            # Extract names, phones, and websites from the page elements
            # (Basic selector pull; can expand as needed)
            entries = page.locator('//a[contains(@href, "/maps/place/")]').all()
            for entry in entries[:5]: # Grab top 5 leads per town to stay fast
                try:
                    title = entry.get_attribute("aria-label") or "Unknown"
                    all_results.append({
                        "Search Term": query,
                        "name": title,
                        "phone": "Available on Maps", # Placeholder fallback
                        "website": "Available on Maps"
                    })
                except:
                    continue
        except Exception as e:
            print(f"Error scraping {query}: {e}")
            
    browser.close()

# 2. Send all collected leads back to your self-hosted n8n instance
if n8n_webhook and all_results:
    requests.post(n8n_webhook, json=all_results)
    print(f"Successfully sent {len(all_results)} leads back to n8n!")

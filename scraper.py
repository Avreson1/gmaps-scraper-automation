import os
import requests
from playwright.sync_api import sync_playwright

# Decode the flat text string back into a clean Python list
queries_env = os.environ.get("SCRAPE_QUERIES", "")
queries = [q.strip() for q in queries_env.split("|||") if q.strip()]

# ✅ FIX 1: Look for the correct nickname key configured in your YAML file
n8n_webhook = os.environ.get("N8N_WEBHOOK_URL")
all_results = []

print(f"Decoded queries string successfully: {queries}")
print(f"Target Webhook: {n8n_webhook}")

if queries and n8n_webhook:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        
        for query in queries:
            print(f"Searching Google Maps for: {query}")
            try:
                # ✅ FIX 2: Navigate to the actual, live Google Maps search engine
                search_url = f"https://www.google.com/maps/search/{requests.utils.quote(query)}"
                page.goto(search_url, wait_until="domcontentloaded")
                
                # Clear Google cookie consent prompts if they appear on the cloud server
                try:
                    consent_btn = page.locator("button:has-text('Accept all'), button:has-text('Agree'), button:has-text('Tout accepter')")
                    if consent_btn.count() > 0:
                        consent_btn.first.click()
                        page.wait_for_timeout(1000)
                except:
                    pass
                
                # Wait up to 10 seconds for map listings to physically load
                page.wait_for_selector('a[href*="/maps/place/"]', timeout=10000)
                
                # Pull business location elements from the panel
                links = page.locator('a[href*="/maps/place/"]').all()
                print(f"Found {len(links)} map items for '{query}'.")
                
                count = 0
                for link in links:
                    if count >= 3: # Limit to top 3 leads per query to keep runtimes optimal
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
                print(f"Note for '{query}': {e}")
                
        browser.close()

# Dispatches data to your active n8n workflow
if n8n_webhook:
    print(f"Firing {len(all_results)} total leads back to n8n.")
    try:
        response = requests.post(n8n_webhook, json=all_results, timeout=120)
        print(f"Successfully reached n8n. Status: {response.status_code}")
    except Exception as e:
        print(f"Failed to send data to webhook: {e}")

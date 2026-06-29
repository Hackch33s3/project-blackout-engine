# scanner.py
import asyncio
import os
from playwright.async_api import async_playwright
from urllib.parse import quote_plus

# CONFIGURATION
# In production, pull these from a .env file or AWS Secrets Manager
PROXY_USERNAME = os.getenv("PROXY_USER", "your_brightdata_user")
PROXY_PASSWORD = os.getenv("PROXY_PASS", "your_brightdata_pass")
PROXY_HOST = os.getenv("PROXY_HOST", "brd.superproxy.io") # Example for BrightData
PROXY_PORT = 22225

async def scan_target(full_name: str, past_city: str):
    """
    Scans major data brokers and search engines for a target's PII.
    Returns a list of dictionaries containing the broker name and profile URL.
    """
    targets_found = []
    
    # Format the search query to mimic a real user looking up a person
    search_query = quote_plus(f'"{full_name}" "{past_city}"')
    
    async with async_playwright() as p:
        # Launch browser with residential proxy to prevent IP bans
        browser = await p.chromium.launch(
            headless=True,
            proxy={
                "server": f"http://{PROXY_HOST}:{PROXY_PORT}",
                "username": PROXY_USERNAME,
                "password": PROXY_PASSWORD,
            }
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        page = await context.new_page()
        
        # --- TARGET 1: TRUEPEOPLESEARCH (Example Logic) ---
        try:
            # Note: In production, you will need to map the exact DOM selectors 
            # for TruePeopleSearch, FastPeopleSearch, etc.
            print(f"[*] Scanning TruePeopleSearch for {full_name}...")
            await page.goto(f"https://www.truepeoplesearch.com/results?name={full_name.replace(' ', '%20')}&citystatezip={past_city}", timeout=30000)
            
            # Wait for the results container to load
            await page.wait_for_selector(".result-card", timeout=10000)
            
            # Extract profile links
            results = await page.query_selector_all(".result-card a[href*='/details']")
            for res in results[:3]: # Limit to top 3 matches
                href = await res.get_attribute("href")
                if href:
                    targets_found.append({
                        "broker": "TruePeopleSearch",
                        "url": f"https://www.truepeoplesearch.com{href}"
                    })
        except Exception as e:
            print(f"[!] TruePeopleSearch scan failed or blocked: {e}")

        # --- TARGET 2: GENERAL GOOGLE DORKING ---
        try:
            print(f"[*] Running Google Dork for {full_name}...")
            # We use a dork to find exact matches on known broker sites
            dork = f'"{full_name}" site:spokeo.com OR site:fastpeoplesearch.com OR site:whitepages.com'
            await page.goto(f"https://www.google.com/search?q={quote_plus(dork)}", timeout=30000)
            await page.wait_for_selector("#search", timeout=10000)
            
            links = await page.query_selector_all("#search a[href]")
            for link in links:
                href = await link.get_attribute("href")
                if href and ("spokeo.com" in href or "fastpeoplesearch.com" in href):
                    targets_found.append({
                        "broker": "Google_Dork_Fetch",
                        "url": href
                    })
        except Exception as e:
            print(f"[!] Google Dork scan failed: {e}")

        await browser.close()
        
    # Deduplicate URLs
    unique_targets = {v['url']:v for v in targets_found}.values()
    return list(unique_targets)

if __name__ == "__main__":
    # TEST RUN
    print("Starting Project BLACKOUT OSINT Scanner...")
    results = asyncio.run(scan_target("John Q. Public", "Toronto, ON"))
    
    print(f"\n[+] SCAN COMPLETE. Found {len(results)} targets:")
    for r in results:
        print(f" - {r['broker']}: {r['url']}")
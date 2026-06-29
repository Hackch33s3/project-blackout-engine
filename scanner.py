from playwright.async_api import async_playwright
from proxy_manager import get_working_proxy
import asyncio

async def run_scan(client_id: str, full_name: str, past_city: str) -> dict:
    targets = []
    
    for attempt in range(1, 4):
        print(f"[*] Attempt {attempt}/3")
        
        proxy = await get_working_proxy()
        
        try:
            async with async_playwright() as p:
                browser_args = {
                    "headless": True,
                    "args": ["--no-sandbox", "--disable-setuid-sandbox"]
                }
                
                if proxy:
                    browser_args["proxy"] = {"server": proxy}
                
                browser = await p.chromium.launch(**browser_args)
                page = await browser.new_page()
                
                # Example: Search for the person
                search_query = f"{full_name} {past_city}"
                await page.goto(f"https://www.google.com/search?q={search_query}")
                await page.wait_for_timeout(2000)
                
                # Extract results (customize this for your use case)
                results = await page.query_selector_all("div.g")
                
                for result in results[:10]:
                    title_elem = await result.query_selector("h3")
                    link_elem = await result.query_selector("a")
                    
                    if title_elem and link_elem:
                        title = await title_elem.inner_text()
                        link = await link_elem.get_attribute("href")
                        
                        targets.append({
                            "title": title,
                            "url": link,
                            "source": "google"
                        })
                
                await browser.close()
                
                print(f"[+] SCAN COMPLETE. Found {len(targets)} targets.")
                return {"targets": targets}
                
        except Exception as e:
            print(f"[!] Browser crashed with proxy {proxy}: {e}")
            continue
    
    print("[+] SCAN COMPLETE. Found 0 targets.")
    return {"targets": []}
from playwright.async_api import async_playwright
from proxy_manager import get_working_proxy
import asyncio
from urllib.parse import quote_plus

BROKER_DOMAINS = [
    "truepeoplesearch.com",
    "fastpeoplesearch.com",
    "spokeo.com",
    "whitepages.com",
    "peoplesearchnow.com",
    "publicrecords.com",
    "beenverified.com",
    "intelius.com",
]

async def run_scan(client_id: str, full_name: str, past_city: str) -> dict:
    targets = []
    search_query = f'"{full_name}" "{past_city}"'

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
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = await context.new_page()

                # --- SOURCE 1: DuckDuckGo HTML search ---
                try:
                    print(f"[*] Searching DuckDuckGo for {full_name}...")
                    await page.goto(f"https://html.duckduckgo.com/html/?q={quote_plus(search_query)}", timeout=30000)
                    await page.wait_for_timeout(2000)

                    results = await page.query_selector_all("a.result__a")
                    for result in results:
                        try:
                            href = await result.get_attribute("href")
                            title = await result.inner_text()
                            if href and any(domain in href for domain in BROKER_DOMAINS):
                                targets.append({
                                    "title": title.strip(),
                                    "url": href,
                                    "broker_name": next(d for d in BROKER_DOMAINS if d in href),
                                    "source": "duckduckgo"
                                })
                        except Exception:
                            continue
                    print(f"[+] DuckDuckGo found {len(targets)} broker results")
                except Exception as e:
                    print(f"[!] DuckDuckGo search failed: {e}")

                # --- SOURCE 2: TruePeopleSearch direct ---
                try:
                    print(f"[*] Scanning TruePeopleSearch directly for {full_name}...")
                    await page.goto(
                        f"https://www.truepeoplesearch.com/results?name={quote_plus(full_name)}&citystatezip={quote_plus(past_city)}",
                        timeout=30000
                    )
                    await page.wait_for_timeout(3000)

                    profile_links = await page.query_selector_all("a[href*='/details']")
                    for link in profile_links[:5]:
                        try:
                            href = await link.get_attribute("href")
                            if href:
                                full_url = href if href.startswith("http") else f"https://www.truepeoplesearch.com{href}"
                                if full_url not in [t["url"] for t in targets]:
                                    targets.append({
                                        "title": f"TruePeopleSearch - {full_name}",
                                        "url": full_url,
                                        "broker_name": "truepeoplesearch.com",
                                        "source": "direct"
                                    })
                        except Exception:
                            continue
                    print(f"[+] TruePeopleSearch direct scan complete")
                except Exception as e:
                    print(f"[!] TruePeopleSearch direct scan failed: {e}")

                # --- SOURCE 3: FastPeopleSearch direct ---
                try:
                    print(f"[*] Scanning FastPeopleSearch directly for {full_name}...")
                    await page.goto(
                        f"https://www.fastpeoplesearch.com/name/{quote_plus(full_name.replace(' ', '-'))}__{quote_plus(past_city.split(',')[0].strip())}",
                        timeout=30000
                    )
                    await page.wait_for_timeout(3000)

                    links = await page.query_selector_all("a[href*='/details']")
                    for link in links[:5]:
                        try:
                            href = await link.get_attribute("href")
                            if href:
                                full_url = href if href.startswith("http") else f"https://www.fastpeoplesearch.com{href}"
                                if full_url not in [t["url"] for t in targets]:
                                    targets.append({
                                        "title": f"FastPeopleSearch - {full_name}",
                                        "url": full_url,
                                        "broker_name": "fastpeoplesearch.com",
                                        "source": "direct"
                                    })
                        except Exception:
                            continue
                    print(f"[+] FastPeopleSearch direct scan complete")
                except Exception as e:
                    print(f"[!] FastPeopleSearch direct scan failed: {e}")

                await browser.close()

                if targets:
                    print(f"[+] SCAN COMPLETE. Found {len(targets)} targets.")
                    return {"targets": targets}

        except Exception as e:
            print(f"[!] Browser crashed with proxy {proxy}: {e}")
            continue

    print("[+] SCAN COMPLETE. Found 0 targets.")
    return {"targets": []}

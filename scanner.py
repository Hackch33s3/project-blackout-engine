from playwright.async_api import async_playwright
from proxy_manager import get_working_proxy
from urllib.parse import quote_plus, unquote, urlparse, parse_qs

BROKER_DOMAINS = [
    "truepeoplesearch.com",
    "fastpeoplesearch.com",
    "spokeo.com",
    "whitepages.com",
    "peoplesearchnow.com",
    "peopledirectory.us",
    "publicrecords.com",
    "beenverified.com",
    "intelius.com",
    "peoplefinders.com",
    "ussearch.com",
    "instantcheckmate.com",
]

def extract_url(href: str) -> str:
    if href.startswith("//"):
        href = "https:" + href
    if "duckduckgo.com/l/" in href or "uddg=" in href:
        parsed = urlparse(href)
        qs = parse_qs(parsed.query)
        if "uddg" in qs:
            return unquote(qs["uddg"][0])
    return href

async def run_scan(client_id: str, full_name: str, past_city: str) -> dict:
    targets = []
    search_query = f'"{full_name}" "{past_city}"'

    for attempt in range(1, 4):
        print(f"[*] Attempt {attempt}/3 for {full_name}")
        proxy = await get_working_proxy()

        try:
            async with async_playwright() as p:
                browser_args = {
                    "headless": True,
                    "args": [
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-web-security",
                        "--disable-features=IsolateOrigins,site-per-process",
                    ]
                }
                if proxy:
                    browser_args["proxy"] = {"server": proxy}

                browser = await p.chromium.launch(**browser_args)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                )
                page = await context.new_page()

                # --- SOURCE 1: DuckDuckGo HTML search ---
                try:
                    print(f"[*] DuckDuckGo: {search_query}")
                    await page.goto(f"https://html.duckduckgo.com/html/?q={quote_plus(search_query)}", timeout=30000)
                    await page.wait_for_timeout(2000)

                    results = await page.query_selector_all("a.result__a")
                    print(f"    -> {len(results)} raw results")
                    for result in results:
                        try:
                            href = await result.get_attribute("href")
                            title = await result.inner_text()
                            url = extract_url(href or "")
                            if url and any(domain in url for domain in BROKER_DOMAINS):
                                broker = next(d for d in BROKER_DOMAINS if d in url)
                                if url not in [t["url"] for t in targets]:
                                    targets.append({
                                        "title": title.strip(),
                                        "url": url,
                                        "broker_name": broker,
                                        "source": "duckduckgo"
                                    })
                                    print(f"    -> FOUND: {broker}")
                        except Exception:
                            continue
                    print(f"[+] DuckDuckGo: {len(targets)} broker matches")
                except Exception as e:
                    print(f"[!] DuckDuckGo failed: {e}")

                # --- SOURCE 2: TruePeopleSearch ---
                try:
                    print(f"[*] TruePeopleSearch: {full_name} {past_city}")
                    tps_urls = [
                        f"https://www.truepeoplesearch.com/results?name={quote_plus(full_name)}&citystatezip={quote_plus(past_city)}",
                        f"https://www.truepeoplesearch.com/results?name={quote_plus(full_name)}",
                    ]
                    for tps_url in tps_urls[:1]:
                        await page.goto(tps_url, timeout=30000, wait_until="domcontentloaded")
                        await page.wait_for_timeout(3000)

                        links = await page.query_selector_all("a[href*='/details']")
                        if not links:
                            links = await page.query_selector_all("a.result-item")
                        for link in links[:5]:
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
                                        print(f"    -> FOUND: TruePeopleSearch")
                            except Exception:
                                continue
                except Exception as e:
                    print(f"[!] TruePeopleSearch failed: {e}")

                # --- SOURCE 3: FastPeopleSearch ---
                try:
                    print(f"[*] FastPeopleSearch: {full_name}")
                    city_slug = past_city.split(",")[0].strip().lower().replace(" ", "-")
                    name_slug = full_name.lower().replace(" ", "-")
                    fps_urls = [
                        f"https://www.fastpeoplesearch.com/name/{name_slug}__{city_slug}",
                        f"https://www.fastpeoplesearch.com/{name_slug}__{city_slug}",
                        f"https://www.fastpeoplesearch.com/name/{quote_plus(full_name)}",
                    ]
                    for fps_url in fps_urls[:2]:
                        await page.goto(fps_url, timeout=30000, wait_until="domcontentloaded")
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
                                        print(f"    -> FOUND: FastPeopleSearch")
                            except Exception:
                                continue
                except Exception as e:
                    print(f"[!] FastPeopleSearch failed: {e}")

                # --- SOURCE 4: PeopleSearchNow ---
                try:
                    print(f"[*] PeopleSearchNow: {full_name}")
                    psn_urls = [
                        f"https://www.peoplesearchnow.com/search?q={quote_plus(full_name)}+{quote_plus(past_city)}",
                        f"https://www.peoplesearchnow.com/search?q={quote_plus(full_name)}",
                    ]
                    for psn_url in psn_urls[:1]:
                        await page.goto(psn_url, timeout=30000, wait_until="domcontentloaded")
                        await page.wait_for_timeout(3000)

                        links = await page.query_selector_all("a[href*='/profile']")
                        for link in links[:5]:
                            try:
                                href = await link.get_attribute("href")
                                if href:
                                    full_url = href if href.startswith("http") else f"https://www.peoplesearchnow.com{href}"
                                    if full_url not in [t["url"] for t in targets]:
                                        targets.append({
                                            "title": f"PeopleSearchNow - {full_name}",
                                            "url": full_url,
                                            "broker_name": "peoplesearchnow.com",
                                            "source": "direct"
                                        })
                                        print(f"    -> FOUND: PeopleSearchNow")
                            except Exception:
                                continue
                except Exception as e:
                    print(f"[!] PeopleSearchNow failed: {e}")

                # --- SOURCE 5: Whitepages ---
                try:
                    print(f"[*] Whitepages: {full_name}")
                    city_slug = past_city.split(",")[0].strip().lower().replace(" ", "-")
                    name_slug = full_name.lower().replace(" ", "-")
                    wp_url = f"https://www.whitepages.com/name/{name_slug}/{city_slug}"
                    await page.goto(wp_url, timeout=30000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(3000)

                    links = await page.query_selector_all("a[href*='/person/']")
                    for link in links[:5]:
                        try:
                            href = await link.get_attribute("href")
                            if href:
                                full_url = href if href.startswith("http") else f"https://www.whitepages.com{href}"
                                if full_url not in [t["url"] for t in targets]:
                                    targets.append({
                                        "title": f"Whitepages - {full_name}",
                                        "url": full_url,
                                        "broker_name": "whitepages.com",
                                        "source": "direct"
                                    })
                                    print(f"    -> FOUND: Whitepages")
                        except Exception:
                            continue
                except Exception as e:
                    print(f"[!] Whitepages failed: {e}")

                await browser.close()

                if targets:
                    print(f"[+] SCAN COMPLETE. Found {len(targets)} targets.")
                    return {"targets": targets}

        except Exception as e:
            print(f"[!] Browser crashed with proxy {proxy}: {e}")
            continue

    print(f"[+] SCAN COMPLETE. Found 0 targets for {full_name}.")
    return {"targets": []}

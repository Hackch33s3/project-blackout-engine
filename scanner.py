from playwright.async_api import async_playwright
from proxy_manager import get_working_proxy
from urllib.parse import quote_plus, unquote, urlparse, parse_qs

BROKER_DOMAINS = [
    "truepeoplesearch.com", "fastpeoplesearch.com", "spokeo.com",
    "whitepages.com", "peoplesearchnow.com", "beenverified.com",
    "intelius.com", "peoplefinders.com", "ussearch.com",
    "instantcheckmate.com", "peekyou.com", "radaris.com",
    "zabasearch.com", "thatsthem.com", "familytreenow.com",
    "searchpeoplefree.com", "mylife.com", "pipl.com",
    "peopledirectory.us", "publicrecords.com", "addresses.com",
    "advancedbackgroundcheck.com", "checkpeople.com",
    "criminalwatchdog.com", "cyberbackgroundchecks.com",
    "findpeoplesearch.com", "graypeoplesearch.com",
    "homemetry.com", "nuwber.com", "peoplelooker.com",
    "quickpeoplesearch.com", "searchquarry.com",
    "smartbackgroundchecks.com", "usphonebook.com", "xlek.com",
]

SCRAPE_SITES = [
    {
        "name": "TruePeopleSearch",
        "url": lambda n, c: f"https://www.truepeoplesearch.com/results?name={quote_plus(n)}&citystatezip={quote_plus(c)}",
        "selectors": ["a[href*='/details']", "a.result-item", "div.card a"],
    },
    {
        "name": "FastPeopleSearch",
        "url": lambda n, c: f"https://www.fastpeoplesearch.com/name/{n.lower().replace(' ', '-')}__{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selectors": ["a[href*='/details']", "a.result-link"],
    },
    {
        "name": "PeopleSearchNow",
        "url": lambda n, c: f"https://www.peoplesearchnow.com/search?q={quote_plus(f'{n} {c.split(',')[0].strip()}')}",
        "selectors": ["a[href*='/profile']", "a[href*='/person/']"],
    },
    {
        "name": "Whitepages",
        "url": lambda n, c: f"https://www.whitepages.com/name/{n.lower().replace(' ', '-')}/{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selectors": ["a[href*='/person/']", "a[href*='/people/']", "a[href*='/result/']"],
    },
    {
        "name": "PeekYou",
        "url": lambda n, c: f"https://www.peekyou.com/{quote_plus(n)}/{quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/peekyou/']", "a[href*='/people/']"],
    },
    {
        "name": "Radaris",
        "url": lambda n, c: f"https://radaris.com/ng/search?q={quote_plus(f'{n} {c.split(',')[0].strip()}')}",
        "selectors": ["a[href*='/p/']"],
    },
    {
        "name": "ThatsThem",
        "url": lambda n, c: f"https://thatsthem.com/name/{quote_plus(n)}/{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selectors": ["a[href*='/person/']"],
    },
    {
        "name": "FamilyTreeNow",
        "url": lambda n, c: f"https://www.familytreenow.com/search/people?q={quote_plus(n)}&city={quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/person/']"],
    },
    {
        "name": "SearchPeopleFree",
        "url": lambda n, c: f"https://www.searchpeoplefree.com/name/{n.lower().replace(' ', '-')}/{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selectors": ["a[href*='/details/']", "a[href*='/person/']"],
    },
    {
        "name": "Nuwber",
        "url": lambda n, c: f"https://nuwber.com/search?name={quote_plus(n)}&city={quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/person/']"],
    },
    {
        "name": "USPhonebook",
        "url": lambda n, c: f"https://www.usphonebook.com/name/{n.lower().replace(' ', '-')}--{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selectors": ["a[href*='/phone/']"],
    },
    {
        "name": "QuickPeopleSearch",
        "url": lambda n, c: f"https://www.quickpeoplesearch.com/name/{n.lower().replace(' ', '-')}__{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selectors": ["a[href*='/details/']"],
    },
    {
        "name": "CheckPeople",
        "url": lambda n, c: f"https://checkpeople.com/search?q={quote_plus(n)}+{quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/person/']"],
    },
    {
        "name": "CyberBackgroundChecks",
        "url": lambda n, c: f"https://www.cyberbackgroundchecks.com/search?q={quote_plus(n)}+{quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/person/']"],
    },
    {
        "name": "Xlek",
        "url": lambda n, c: f"https://www.xlek.com/search?q={quote_plus(n)}",
        "selectors": ["a[href*='/person/']"],
    },
    {
        "name": "AdvancedBackgroundCheck",
        "url": lambda n, c: f"https://www.advancedbackgroundcheck.com/search?q={quote_plus(n)}+{quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/results/']"],
    },
    {
        "name": "CriminalWatchdog",
        "url": lambda n, c: f"https://www.criminalwatchdog.com/search?q={quote_plus(n)}&location={quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/record/']"],
    },
    {
        "name": "Homemetry",
        "url": lambda n, c: f"https://homemetry.com/search?q={quote_plus(f'{n} {c.split(',')[0].strip()}')}",
        "selectors": ["a[href*='/property/']"],
    },
    {
        "name": "ZabaSearch",
        "url": lambda n, c: f"https://www.zabasearch.com/people/{quote_plus(n)}+{quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/people/']"],
    },
]


def extract_url(href: str) -> str:
    if not href:
        return ""
    if href.startswith("//"):
        href = "https:" + href
    if "duckduckgo.com/l/" in href or "uddg=" in href:
        parsed = urlparse(href)
        qs = parse_qs(parsed.query)
        if "uddg" in qs:
            return unquote(qs["uddg"][0])
    return href


async def try_direct(page, url: str, timeout: int = 25000) -> str:
    try:
        resp = await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        status = resp.status if resp else 0
        title = await page.title()
        return f"HTTP {status} — {title[:80]}"
    except Exception as e:
        err = str(e)[:100]
        return f"FAILED: {err}"


async def run_scan(client_id: str, full_name: str, past_city: str) -> dict:
    all_targets = []

    for attempt in range(1, 4):
        print(f"\n[*] === Attempt {attempt}/3 for {full_name} ===")
        proxy = None
        if attempt > 1:
            proxy = await get_working_proxy()

        try:
            async with async_playwright() as p:
                launch_args = {
                    "headless": True,
                    "args": [
                        "--no-sandbox", "--disable-setuid-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-web-security",
                        "--disable-features=IsolateOrigins,site-per-process",
                        "--disable-dev-shm-usage",
                    ]
                }
                if proxy:
                    launch_args["proxy"] = {"server": proxy}
                    print(f"    proxy={proxy}")
                else:
                    print("    proxy=direct")

                browser = await p.chromium.launch(**launch_args)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                )
                page = await context.new_page()

                # Phase 1: DuckDuckGo (only direct, proxies break HTTPS certs)
                if not proxy:
                    try:
                        q = f'"{full_name}" "{past_city}"'
                        print(f"[1/4] DuckDuckGo")
                        await page.goto(
                            f"https://html.duckduckgo.com/html/?q={quote_plus(q)}",
                            timeout=25000, wait_until="domcontentloaded"
                        )
                        await page.wait_for_timeout(2000)

                        results = await page.query_selector_all("a.result__a")
                        print(f"      {len(results)} results")
                        for r in results:
                            try:
                                href = await r.get_attribute("href")
                                title = await r.inner_text()
                                url = extract_url(href or "")
                                if url and any(d in url for d in BROKER_DOMAINS):
                                    broker = next(d for d in BROKER_DOMAINS if d in url)
                                    if url not in [t["url"] for t in all_targets]:
                                        all_targets.append({
                                            "title": title.strip(),
                                            "url": url,
                                            "broker_name": broker,
                                            "source": "search"
                                        })
                                        print(f"      -> {broker}")
                            except Exception:
                                continue
                    except Exception as e:
                        print(f"      FAILED: {str(e)[:80]}")
                else:
                    print("[1/4] DuckDuckGo — skipped (proxy+HTTPS cert issue)")

                # Phase 2: Direct broker scraping
                total = len(SCRAPE_SITES)
                for idx, site in enumerate(SCRAPE_SITES, 1):
                    broker_name = site["name"]
                    if broker_name == "ZabaSearch":
                        print(f"[4/4] ZabaSearch + remaining brokers")
                    elif any(t["broker_name"].replace(".com","") == broker_name.lower() for t in all_targets):
                        continue

                    url = site["url"](full_name, past_city)
                    if "blocked" in url.lower() or "captcha" in url.lower():
                        continue

                    result = await try_direct(page, url)
                    print(f"  {broker_name:25s} {result}")

                    if "FAILED" in result or "404" in result or "500" in result:
                        continue
                    if "captcha" in result.lower() or "blocked" in result.lower() or "access denied" in result.lower():
                        continue

                    for selector in site["selectors"]:
                        links = await page.query_selector_all(selector)
                        if links:
                            for link in links[:5]:
                                try:
                                    href = await link.get_attribute("href")
                                    if href:
                                        prefix = f"https://www.{broker_name.lower()}.com"
                                        if "peekyou" in prefix:
                                            prefix = "https://peekyou.com"
                                        elif "radaris" in prefix:
                                            prefix = "https://radaris.com"
                                        elif "thatsthem" in prefix:
                                            prefix = "https://thatsthem.com"
                                        elif "nuwber" in prefix:
                                            prefix = "https://nuwber.com"
                                        elif "homemetry" in prefix:
                                            prefix = "https://homemetry.com"
                                        elif "xlek" in prefix:
                                            prefix = "https://www.xlek.com"
                                        full_url = href if href.startswith("http") else f"{prefix}{href}"
                                        if full_url not in [t["url"] for t in all_targets]:
                                            all_targets.append({
                                                "title": f"{broker_name} - {full_name}",
                                                "url": full_url,
                                                "broker_name": broker_name.lower().replace(" ", "") + ".com",
                                                "source": "direct"
                                            })
                                            print(f"      -> FOUND: {broker_name}")
                                except Exception:
                                    continue
                            break

                await browser.close()

                if all_targets:
                    print(f"\n[+] SCAN COMPLETE. Found {len(all_targets)} targets.")
                    return {"targets": all_targets}

        except Exception as e:
            print(f"[!] Browser crashed: {str(e)[:120]}")
            continue

    print(f"\n[+] SCAN COMPLETE. Found 0 targets.")
    return {"targets": []}

from playwright.async_api import async_playwright
from proxy_manager import get_working_proxy
from urllib.parse import quote_plus, unquote, urlparse, parse_qs

def ddg(t, n, c):
    return t(n, c)

PHASE_1_SITES = [
    {
        "name": "TruePeopleSearch",
        "url": lambda n, c: f"https://www.truepeoplesearch.com/results?name={quote_plus(n)}&citystatezip={quote_plus(c)}",
        "selectors": ["a[href*='/details']"],
        "prefix": "https://www.truepeoplesearch.com",
    },
    {
        "name": "FastPeopleSearch",
        "url": lambda n, c: f"https://www.fastpeoplesearch.com/name/{n.lower().replace(' ', '-')}__{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selectors": ["a[href*='/details']"],
        "prefix": "https://www.fastpeoplesearch.com",
    },
    {
        "name": "PeopleSearchNow",
        "url": lambda n, c: f"https://www.peoplesearchnow.com/search?q={quote_plus(f'{n} {c.split(',')[0].strip()}')}",
        "selectors": ["a[href*='/profile']"],
        "prefix": "https://www.peoplesearchnow.com",
    },
    {
        "name": "SearchPeopleFree",
        "url": lambda n, c: f"https://www.searchpeoplefree.com/name/{n.lower().replace(' ', '-')}/{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selectors": ["a[href*='/details/']"],
        "prefix": "https://www.searchpeoplefree.com",
    },
    {
        "name": "FamilyTreeNow",
        "url": lambda n, c: f"https://www.familytreenow.com/search/people?q={quote_plus(n)}&city={quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/person/']"],
        "prefix": "https://www.familytreenow.com",
    },
    {
        "name": "USPhonebook",
        "url": lambda n, c: f"https://www.usphonebook.com/name/{n.lower().replace(' ', '-')}--{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selectors": ["a[href*='/phone/']"],
        "prefix": "https://www.usphonebook.com",
    },
    {
        "name": "QuickPeopleSearch",
        "url": lambda n, c: f"https://www.quickpeoplesearch.com/name/{n.lower().replace(' ', '-')}__{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selectors": ["a[href*='/details/']"],
        "prefix": "https://www.quickpeoplesearch.com",
    },
    {
        "name": "AdvancedCheck",
        "url": lambda n, c: f"https://www.advancedbackgroundcheck.com/search?q={quote_plus(n)}+{quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/results/']"],
        "prefix": "https://www.advancedbackgroundcheck.com",
    },
    {
        "name": "CriminalWatchdog",
        "url": lambda n, c: f"https://www.criminalwatchdog.com/search?q={quote_plus(n)}&location={quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/record/']"],
        "prefix": "https://www.criminalwatchdog.com",
    },
    {
        "name": "CyberChecks",
        "url": lambda n, c: f"https://www.cyberbackgroundchecks.com/search?q={quote_plus(n)}+{quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/person/']"],
        "prefix": "https://www.cyberbackgroundchecks.com",
    },
    {
        "name": "Whitepages",
        "url": lambda n, c: f"https://www.whitepages.com/name/{n.lower().replace(' ', '-')}/{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selectors": ["a[href*='/person/']"],
        "prefix": "https://www.whitepages.com",
    },
    {
        "name": "PeekYou",
        "url": lambda n, c: f"https://www.peekyou.com/{quote_plus(n)}/{quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/peekyou/']"],
        "prefix": "https://peekyou.com",
    },
    {
        "name": "Radaris",
        "url": lambda n, c: f"https://radaris.com/ng/search?q={quote_plus(f'{n} {c.split(',')[0].strip()}')}",
        "selectors": ["a[href*='/p/']"],
        "prefix": "https://radaris.com",
    },
    {
        "name": "ThatsThem",
        "url": lambda n, c: f"https://thatsthem.com/name/{quote_plus(n)}/{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selectors": ["a[href*='/person/']"],
        "prefix": "https://thatsthem.com",
    },
    {
        "name": "Nuwber",
        "url": lambda n, c: f"https://nuwber.com/search?name={quote_plus(n)}&city={quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/person/']"],
        "prefix": "https://nuwber.com",
    },
    {
        "name": "ZabaSearch",
        "url": lambda n, c: f"https://www.zabasearch.com/people/{quote_plus(n)}+{quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/people/']"],
        "prefix": "",
    },
    {
        "name": "CheckPeople",
        "url": lambda n, c: f"https://checkpeople.com/search?q={quote_plus(n)}+{quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/person/']"],
        "prefix": "",
    },
    {
        "name": "Xlek",
        "url": lambda n, c: f"https://www.xlek.com/search?q={quote_plus(n)}",
        "selectors": ["a[href*='/person/']"],
        "prefix": "https://www.xlek.com",
    },
    {
        "name": "Homemetry",
        "url": lambda n, c: f"https://homemetry.com/search?q={quote_plus(f'{n} {c.split(',')[0].strip()}')}",
        "selectors": ["a[href*='/property/']"],
        "prefix": "",
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


async def run_scan(client_id: str, full_name: str, past_city: str) -> dict:
    all_targets = []
    search_query = f'"{full_name}" "{past_city}"'

    for attempt in range(1, 4):
        print(f"\n=== Attempt {attempt}/3 for {full_name} ===")
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
                        "--disable-dev-shm-usage",
                    ]
                }
                if proxy:
                    launch_args["proxy"] = {"server": proxy}
                    print(f"proxy: {proxy}")
                else:
                    print("proxy: direct")

                browser = await p.chromium.launch(**launch_args)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                )
                page = await context.new_page()

                # ---- DuckDuckGo search (direct only, proxy breaks HTTPS) ----
                if not proxy:
                    try:
                        print("  DuckDuckGo  search...", end=" ")
                        await page.goto(
                            f"https://html.duckduckgo.com/html/?q={quote_plus(search_query)}",
                            timeout=25000, wait_until="domcontentloaded"
                        )
                        await page.wait_for_timeout(2000)
                        results = await page.query_selector_all("a.result__a")
                        found = 0
                        for r in results:
                            try:
                                href = await r.get_attribute("href")
                                title = await r.inner_text()
                                url = extract_url(href or "")
                                if url and any(d in url for d in
                                    ["truepeople", "fastpeople", "peoplesearchnow", "whitepages",
                                     "peekyou", "radaris", "thatsthem", "familytreenow",
                                     "searchpeoplefree", "nuwber", "usphonebook",
                                     "advancedbackgroundcheck", "criminalwatchdog",
                                     "quickpeoplesearch", "checkpeople", "cyberbackground",
                                     "xlek", "homemetry", "zabasearch"]):
                                    if url not in [t["url"] for t in all_targets]:
                                        all_targets.append({
                                            "title": title.strip(),
                                            "url": url,
                                            "broker_name": url.split("/")[2].replace("www.", ""),
                                            "source": "search",
                                        })
                                        found += 1
                            except Exception:
                                continue
                        print(f"{found} broker links")
                    except Exception as e:
                        print(f"FAILED — {str(e)[:60]}")
                else:
                    print("  DuckDuckGo  skipped (proxy)")

                # ---- Direct broker scraping ----
                for site in PHASE_1_SITES:
                    name = site["name"]
                    if any(t.get("broker_name", "").replace("www.", "") in name.lower()
                           or name.lower() in t.get("broker_name", "").lower()
                           for t in all_targets):
                        continue

                    url = site["url"](full_name, past_city)
                    try:
                        resp = await page.goto(url, timeout=20000, wait_until="domcontentloaded")
                        await page.wait_for_timeout(2000)
                        status = resp.status if resp else 0

                        if status not in (200, 301, 302):
                            print(f"  {name:20s} HTTP {status}")
                            continue

                        text = await page.content()
                        if any(w in text.lower() for w in ["captcha", "access denied", "automated"]):
                            print(f"  {name:20s} blocked")
                            continue

                        found = 0
                        for sel in site["selectors"]:
                            links = await page.query_selector_all(sel)
                            if not links:
                                continue
                            pfx = site["prefix"]
                            for link in links[:5]:
                                try:
                                    href = await link.get_attribute("href")
                                    if not href:
                                        continue
                                    full = href if href.startswith("http") else f"{pfx}{href}"
                                    if full not in [t["url"] for t in all_targets]:
                                        all_targets.append({
                                            "title": f"{name} - {full_name}",
                                            "url": full,
                                            "broker_name": f"{name.lower()}.com",
                                            "source": "direct",
                                        })
                                        found += 1
                                except Exception:
                                    continue
                            if found:
                                break

                        if found:
                            print(f"  {name:20s} {found} found")
                        else:
                            print(f"  {name:20s} HTTP {status}")

                    except Exception as e:
                        print(f"  {name:20s} ERR — {str(e)[:60]}")

                await browser.close()

                if all_targets:
                    print(f"\n[+] SCAN COMPLETE. Found {len(all_targets)} targets.")
                    return {"targets": all_targets}

        except Exception as e:
            print(f"[!] Browser crash: {str(e)[:100]}")
            continue

    print(f"\n[+] SCAN COMPLETE. Found 0 targets.")
    return {"targets": []}

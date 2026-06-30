from playwright.async_api import async_playwright
from proxy_manager import get_working_proxy
from urllib.parse import quote_plus, unquote, urlparse, parse_qs
import time

BROKER_DOMAINS = [
    "truepeoplesearch.com", "fastpeoplesearch.com", "spokeo.com",
    "whitepages.com", "peoplesearchnow.com", "beenverified.com",
    "intelius.com", "peoplefinders.com", "ussearch.com",
    "instantcheckmate.com", "peekyou.com", "radaris.com",
    "zabasearch.com", "thatsthem.com", "familytreenow.com",
    "searchpeoplefree.com", "mylife.com", "pipl.com",
    "peopledirectory.us", "publicrecords.com", "addresses.com",
    "advancedbackgroundcheck.com", "checkpeople.com",
    "cocodoc.com", "criminalwatchdog.com", "cubilis.com",
    "cyberbackgroundchecks.com", "dochub.com", "expertcheck.com",
    "findpeoplesearch.com", "freebackgroundcheck.org",
    "freepeoplesearch.org", "googlesource.com", "govdeprecated.com",
    "governmentregistry.org", "graypeoplesearch.com",
    "homemetry.com", "identitypi.com", "idtrue.com",
    "inteliuslocation.com", "locatefamily.com", "lookup.com",
    "neighborreport.com", "netronline.com", "newenglandfacts.com",
    "nuwber.com", "people-search.net", "people-tracer.com",
    "peoplesearch.com", "peoplewhiz.com", "phonebooks.com",
    "publiceye.com", "publicrecordsnow.com", "publicrecordssearch.com",
    "quickpeoplesearch.com", "rehold.com", "searchpeople.org",
    "searchquarry.com", "skopenow.com", "smartbackgroundchecks.com",
    "socialcatfish.com", "truepeoplesearch.net", "trustedpeoplesearch.com",
    "unmask.com", "us-people-search.com", "usphonebook.com",
    "verifypeople.com", "xlek.com", "peoplelooker.com",
    "addresssearch.com", "phonenumber.com", "peoplesearch.xyz",
]

SCRAPE_SITES = [
    {
        "name": "TruePeopleSearch",
        "domain": "truepeoplesearch.com",
        "url": lambda n, c: f"https://www.truepeoplesearch.com/results?name={quote_plus(n)}&citystatezip={quote_plus(c)}",
        "selector": "a[href*='/details']",
        "prefix": "https://www.truepeoplesearch.com",
    },
    {
        "name": "FastPeopleSearch",
        "domain": "fastpeoplesearch.com",
        "url": lambda n, c: f"https://www.fastpeoplesearch.com/name/{n.lower().replace(' ', '-')}__{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selector": "a[href*='/details']",
        "prefix": "https://www.fastpeoplesearch.com",
    },
    {
        "name": "PeopleSearchNow",
        "domain": "peoplesearchnow.com",
        "url": lambda n, c: f"https://www.peoplesearchnow.com/search?q={quote_plus(f'{n} {c.split(',')[0].strip()}')}",
        "selector": "a[href*='/profile']",
        "prefix": "https://www.peoplesearchnow.com",
    },
    {
        "name": "Whitepages",
        "domain": "whitepages.com",
        "url": lambda n, c: f"https://www.whitepages.com/name/{n.lower().replace(' ', '-')}/{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selector": "a[href*='/person/'], a[href*='/people/']",
        "prefix": "https://www.whitepages.com",
    },
    {
        "name": "PeekYou",
        "domain": "peekyou.com",
        "url": lambda n, c: f"https://www.peekyou.com/{quote_plus(n)}/{quote_plus(c.split(',')[0].strip())}",
        "selector": "a[href*='/peekyou/'], a[href*='/people/']",
        "prefix": "https://peekyou.com",
    },
    {
        "name": "Radaris",
        "domain": "radaris.com",
        "url": lambda n, c: f"https://radaris.com/ng/search?q={quote_plus(f'{n} {c.split(',')[0].strip()}')}",
        "selector": "a[href*='/p/']",
        "prefix": "https://radaris.com",
    },
    {
        "name": "ThatsThem",
        "domain": "thatsthem.com",
        "url": lambda n, c: f"https://thatsthem.com/name/{quote_plus(n)}/{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selector": "a[href*='/person/'], a[href*='/people/']",
        "prefix": "https://thatsthem.com",
    },
    {
        "name": "ZabaSearch",
        "domain": "zabasearch.com",
        "url": lambda n, c: f"https://www.zabasearch.com/people/{quote_plus(n)}+{quote_plus(c.split(',')[0].strip())}",
        "selector": "a[href*='/people/'], a.result-item",
        "prefix": "",
    },
    {
        "name": "FamilyTreeNow",
        "domain": "familytreenow.com",
        "url": lambda n, c: f"https://www.familytreenow.com/search/people?q={quote_plus(n)}&city={quote_plus(c.split(',')[0].strip())}",
        "selector": "a[href*='/person/']",
        "prefix": "https://www.familytreenow.com",
    },
    {
        "name": "SearchPeopleFree",
        "domain": "searchpeoplefree.com",
        "url": lambda n, c: f"https://www.searchpeoplefree.com/name/{n.lower().replace(' ', '-')}/{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selector": "a[href*='/details/'], a[href*='/person/']",
        "prefix": "https://www.searchpeoplefree.com",
    },
    {
        "name": "CriminalWatchdog",
        "domain": "criminalwatchdog.com",
        "url": lambda n, c: f"https://www.criminalwatchdog.com/search?q={quote_plus(n)}&location={quote_plus(c.split(',')[0].strip())}",
        "selector": "a[href*='/person/'], a[href*='/record/']",
        "prefix": "https://www.criminalwatchdog.com",
    },
    {
        "name": "Nuwber",
        "domain": "nuwber.com",
        "url": lambda n, c: f"https://nuwber.com/search?name={quote_plus(n)}&city={quote_plus(c.split(',')[0].strip())}",
        "selector": "a[href*='/person/']",
        "prefix": "https://nuwber.com",
    },
    {
        "name": "USPhonebook",
        "domain": "usphonebook.com",
        "url": lambda n, c: f"https://www.usphonebook.com/name/{n.lower().replace(' ', '-')}--{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selector": "a[href*='/phone/']",
        "prefix": "https://www.usphonebook.com",
    },
    {
        "name": "AdvancedBackgroundCheck",
        "domain": "advancedbackgroundcheck.com",
        "url": lambda n, c: f"https://www.advancedbackgroundcheck.com/search?q={quote_plus(n)}+{quote_plus(c.split(',')[0].strip())}",
        "selector": "a[href*='/results/']",
        "prefix": "https://www.advancedbackgroundcheck.com",
    },
    {
        "name": "QuickPeopleSearch",
        "domain": "quickpeoplesearch.com",
        "url": lambda n, c: f"https://www.quickpeoplesearch.com/name/{n.lower().replace(' ', '-')}__{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selector": "a[href*='/details/']",
        "prefix": "https://www.quickpeoplesearch.com",
    },
    {
        "name": "CheckPeople",
        "domain": "checkpeople.com",
        "url": lambda n, c: f"https://checkpeople.com/search?q={quote_plus(n)}+{quote_plus(c.split(',')[0].strip())}",
        "selector": "a[href*='/person/'], a[href*='/people/']",
        "prefix": "",
    },
    {
        "name": "CyberBackgroundChecks",
        "domain": "cyberbackgroundchecks.com",
        "url": lambda n, c: f"https://www.cyberbackgroundchecks.com/search?q={quote_plus(n)}+{quote_plus(c.split(',')[0].strip())}",
        "selector": "a[href*='/person/']",
        "prefix": "",
    },
    {
        "name": "Xlek",
        "domain": "xlek.com",
        "url": lambda n, c: f"https://www.xlek.com/search?q={quote_plus(n)}",
        "selector": "a[href*='/person/']",
        "prefix": "https://www.xlek.com",
    },
    {
        "name": "Homemetry",
        "domain": "homemetry.com",
        "url": lambda n, c: f"https://homemetry.com/search?q={quote_plus(f'{n} {c.split(',')[0].strip()}')}",
        "selector": "a[href*='/property/'], a[href*='/person/']",
        "prefix": "",
    },
    {
        "name": "PeopleLooker",
        "domain": "peoplelooker.com",
        "url": lambda n, c: f"https://www.peoplelooker.com/search?q={quote_plus(f'{n} {c.split(',')[0].strip()}')}",
        "selector": "a[href*='/person/']",
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
        print(f"[*] === Attempt {attempt}/3 for {full_name} ===")
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

                browser = await p.chromium.launch(**launch_args)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                    permissions=["geolocation"],
                )
                page = await context.new_page()

                # --- PHASE 1: DuckDuckGo wide search across all broker domains ---
                try:
                    print(f"[*] DuckDuckGo search: {full_name}")
                    await page.goto(
                        f"https://html.duckduckgo.com/html/?q={quote_plus(search_query)}",
                        timeout=30000, wait_until="domcontentloaded"
                    )
                    await page.wait_for_timeout(2000)

                    results = await page.query_selector_all("a.result__a")
                    print(f"    -> {len(results)} raw results from DuckDuckGo")
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
                                    print(f"    -> SEARCH FOUND: {broker}")
                        except Exception:
                            continue
                    print(f"[+] DuckDuckGo: {sum(1 for t in all_targets if t['source'] == 'search')} matches")
                except Exception as e:
                    print(f"[!] DuckDuckGo failed: {e}")

                # --- PHASE 2: Direct scraping of known broker sites ---
                for site in SCRAPE_SITES:
                    broker_name = site["name"]
                    domain = site["domain"]
                    if any(t["broker_name"] == domain for t in all_targets):
                        continue

                    try:
                        url = site["url"](full_name, past_city)
                        print(f"[*] {broker_name}")
                        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        await page.wait_for_timeout(3000)

                        page_source = await page.content()
                        if "captcha" in page_source.lower() or "blocked" in page_source.lower() or "automated" in page_source.lower():
                            print(f"    -> blocked or captcha")
                            continue

                        selectors = site["selector"].split(", ")
                        links = []
                        for sel in selectors:
                            links = await page.query_selector_all(sel)
                            if links:
                                break

                        found = 0
                        for link in links[:5]:
                            try:
                                href = await link.get_attribute("href")
                                if href:
                                    prefix = site["prefix"]
                                    full_url = href if href.startswith("http") else f"{prefix}{href}"
                                    if full_url not in [t["url"] for t in all_targets]:
                                        all_targets.append({
                                            "title": f"{broker_name} - {full_name}",
                                            "url": full_url,
                                            "broker_name": domain,
                                            "source": "direct"
                                        })
                                        found += 1
                            except Exception:
                                continue
                        if found:
                            print(f"    -> FOUND {found}")
                    except Exception as e:
                        pass

                    await page.wait_for_timeout(1000)

                await browser.close()

                if all_targets:
                    print(f"[+] SCAN COMPLETE. Found {len(all_targets)} total targets.")
                    return {"targets": all_targets}

        except Exception as e:
            print(f"[!] Browser crashed: {e}")
            continue

    print(f"[+] SCAN COMPLETE. Found 0 targets for {full_name}.")
    return {"targets": []}

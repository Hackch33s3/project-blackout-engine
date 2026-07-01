from playwright.async_api import async_playwright
from urllib.parse import quote_plus, unquote, urlparse, parse_qs

PHASE_1 = [
    {
        "name": "TruePeopleSearch",
        "domain": "truepeoplesearch.com",
        "url": lambda n, c: f"https://www.truepeoplesearch.com/results?name={quote_plus(n)}&citystatezip={quote_plus(c)}",
        "selectors": ["a[href*='/details']"],
    },
    {
        "name": "FastPeopleSearch",
        "domain": "fastpeoplesearch.com",
        "url": lambda n, c: f"https://www.fastpeoplesearch.com/name/{n.lower().replace(' ', '-')}__{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selectors": ["a[href*='/details']"],
    },
    {
        "name": "PeopleSearchNow",
        "domain": "peoplesearchnow.com",
        "url": lambda n, c: f"https://www.peoplesearchnow.com/search?q={quote_plus(f'{n} {c.split(',')[0].strip()}')}",
        "selectors": ["a[href*='/profile']"],
    },
    {
        "name": "SearchPeopleFree",
        "domain": "searchpeoplefree.com",
        "url": lambda n, c: f"https://www.searchpeoplefree.com/name/{n.lower().replace(' ', '-')}/{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selectors": ["a[href*='/details/']"],
    },
    {
        "name": "FamilyTreeNow",
        "domain": "familytreenow.com",
        "url": lambda n, c: f"https://www.familytreenow.com/search/people?q={quote_plus(n)}&city={quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/person/']"],
    },
    {
        "name": "USPhonebook",
        "domain": "usphonebook.com",
        "url": lambda n, c: f"https://www.usphonebook.com/name/{n.lower().replace(' ', '-')}--{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selectors": ["a[href*='/phone/']"],
    },
    {
        "name": "QuickPeopleSearch",
        "domain": "quickpeoplesearch.com",
        "url": lambda n, c: f"https://www.quickpeoplesearch.com/name/{n.lower().replace(' ', '-')}__{c.split(',')[0].strip().lower().replace(' ', '-')}",
        "selectors": ["a[href*='/details/']"],
    },
    {
        "name": "AdvancedBackgroundCheck",
        "domain": "advancedbackgroundcheck.com",
        "url": lambda n, c: f"https://www.advancedbackgroundcheck.com/search?q={quote_plus(n)}+{quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/results/']"],
    },
    {
        "name": "CriminalWatchdog",
        "domain": "criminalwatchdog.com",
        "url": lambda n, c: f"https://www.criminalwatchdog.com/search?q={quote_plus(n)}&location={quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/record/']"],
    },
    {
        "name": "CyberBackgroundChecks",
        "domain": "cyberbackgroundchecks.com",
        "url": lambda n, c: f"https://www.cyberbackgroundchecks.com/search?q={quote_plus(n)}+{quote_plus(c.split(',')[0].strip())}",
        "selectors": ["a[href*='/person/']"],
    },
]

PHASE_2 = []
PHASE_3 = []

ALL_TIERS = [("Phase 1", PHASE_1), ("Phase 2", PHASE_2), ("Phase 3", PHASE_3)]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
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

async def try_goto(page, url: str, timeout: int = 20000) -> tuple[int, str]:
    try:
        resp = await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        status = resp.status if resp else 0
        title = await page.title()
        return status, title[:100]
    except Exception as e:
        return 0, str(e)[:100]

def make_prefix(domain: str) -> str:
    overrides = {
        "radaris.com": "https://radaris.com",
        "peekyou.com": "https://peekyou.com",
        "nuwber.com": "https://nuwber.com",
        "thatsthem.com": "https://thatsthem.com",
        "homemetry.com": "https://homemetry.com",
        "xlek.com": "https://www.xlek.com",
    }
    return overrides.get(domain, f"https://www.{domain}")

async def run_scan(client_id: str, full_name: str, past_city: str) -> dict:
    all_targets = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox", "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        )

        for tier_name, sites in ALL_TIERS:
            if not sites:
                continue

            print(f"\n=== {tier_name} ({len(sites)} brokers) ===")

            context = await browser.new_context(
                user_agent=USER_AGENTS[0],
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
            )
            page = await context.new_page()

            for site in sites:
                name = site["name"]
                domain = site["domain"]

                if any(t["broker_name"] == domain for t in all_targets):
                    continue

                url = site["url"](full_name, past_city)
                status, info = await try_goto(page, url)
                icon = "+" if status == 200 else " "
                print(f"  [{icon}] {name:25s} HTTP {status}")

                if status not in (200, 301, 302):
                    continue

                body = await page.content()
                if any(w in body.lower() for w in ["captcha", "access denied", "automated"]):
                    print(f"         blocked")
                    continue

                found = 0
                for selector in site["selectors"]:
                    links = await page.query_selector_all(selector)
                    if not links:
                        continue
                    prefix = make_prefix(domain)
                    for link in links[:5]:
                        try:
                            href = await link.get_attribute("href")
                            if not href:
                                continue
                            full = href if href.startswith("http") else f"{prefix}{href}"
                            if full not in [t["url"] for t in all_targets]:
                                all_targets.append({
                                    "title": f"{name} - {full_name}",
                                    "url": full,
                                    "broker_name": domain,
                                    "source": "direct",
                                })
                                found += 1
                        except Exception:
                            continue
                    if found:
                        break

                if found:
                    print(f"         found {found}")

            await context.close()

        await browser.close()

    print(f"\n[+] SCAN COMPLETE. Found {len(all_targets)} targets.")
    return {"targets": all_targets}

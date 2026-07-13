from playwright.async_api import async_playwright
from urllib.parse import quote_plus, unquote, urlparse, parse_qs
import os

# ---------------------------------------------------------------------------
# Location parsing (province-aware)
# ---------------------------------------------------------------------------
# The old code did `c.split(",")[0]` for the city and assumed a US-style
# URL. That breaks on Canadian input ("Toronto, ON") — the province is
# dropped and US-only URL builders mis-fire. We now parse city / province /
# country explicitly and route to the correct broker list.

PROVINCE_CODES = {
    "AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU",
    "ON", "PE", "QC", "SK", "YT",
}
PROVINCE_NAMES = {
    "alberta": "AB", "british columbia": "BC", "manitoba": "MB",
    "new brunswick": "NB", "newfoundland": "NL", "newfoundland and labrador": "NL",
    "nova scotia": "NS", "northwest territories": "NT", "nunavut": "NU",
    "ontario": "ON", "prince edward island": "PE", "quebec": "QC",
    "saskatchewan": "SK", "yukon": "YT",
}


def parse_location(past_city: str) -> dict:
    """Return {city, province, country} from a free-text location.

    Examples:
        "Toronto, ON"        -> city=Toronto, province=ON, country=CA
        "Toronto, Ontario"   -> city=Toronto, province=ON, country=CA
        "Toronto, Canada"    -> city=Toronto, province="", country=CA
        "Springfield, IL"    -> city=Springfield, province=IL, country=US
        "Springfield"        -> city=Springfield, province="", country=""
    """
    raw = (past_city or "").strip()
    if "," in raw:
        parts = [p.strip() for p in raw.split(",")]
        city = parts[0]
        tail = parts[-1]            # last token carries province / country
    else:
        parts = [raw]
        city = raw
        tail = ""

    city = city.strip()
    province = ""
    country = ""

    t_up = tail.upper()
    t_lo = tail.lower()
    if t_up in PROVINCE_CODES:
        province = t_up
        country = "CA"
    elif t_lo in PROVINCE_NAMES:
        province = PROVINCE_NAMES[t_lo]
        country = "CA"
    elif t_lo in ("canada", "ca"):
        country = "CA"
    elif t_lo in ("usa", "us", "united states", "america"):
        country = "US"
    elif len(tail) == 2 and tail.isupper() and tail not in PROVINCE_CODES:
        # Two-letter tail that isn't a CA province is treated as a US state.
        country = "US"
        province = tail

    return {"city": city, "province": province, "country": country}


# ---------------------------------------------------------------------------
# US broker list (unchanged behaviour, but URL builders now use loc["city"])
# ---------------------------------------------------------------------------

PHASE_1_SITES = [
    {
        "name": "TruePeopleSearch",
        "url": lambda n, loc: f"https://www.truepeoplesearch.com/results?name={quote_plus(n)}&citystatezip={quote_plus(loc['city'])}",
        "selectors": ["a[href*='/details']"],
        "prefix": "https://www.truepeoplesearch.com",
    },
    {
        "name": "FastPeopleSearch",
        "url": lambda n, loc: f"https://www.fastpeoplesearch.com/name/{n.lower().replace(' ', '-')}__{loc['city'].lower().replace(' ', '-')}",
        "selectors": ["a[href*='/details']"],
        "prefix": "https://www.fastpeoplesearch.com",
    },
    {
        "name": "PeopleSearchNow",
        "url": lambda n, loc: "https://www.peoplesearchnow.com/search?q=" + quote_plus(n + " " + loc["city"]),
        "selectors": ["a[href*='/profile']"],
        "prefix": "https://www.peoplesearchnow.com",
    },
    {
        "name": "SearchPeopleFree",
        "url": lambda n, loc: f"https://www.searchpeoplefree.com/name/{n.lower().replace(' ', '-')}/{loc['city'].lower().replace(' ', '-')}",
        "selectors": ["a[href*='/details/']"],
        "prefix": "https://www.searchpeoplefree.com",
    },
    {
        "name": "FamilyTreeNow",
        "url": lambda n, loc: f"https://www.familytreenow.com/search/people?q={quote_plus(n)}&city={quote_plus(loc['city'])}",
        "selectors": ["a[href*='/person/']"],
        "prefix": "https://www.familytreenow.com",
    },
    {
        "name": "USPhonebook",
        "url": lambda n, loc: f"https://www.usphonebook.com/name/{n.lower().replace(' ', '-')}--{loc['city'].lower().replace(' ', '-')}",
        "selectors": ["a[href*='/phone/']"],
        "prefix": "https://www.usphonebook.com",
    },
    {
        "name": "QuickPeopleSearch",
        "url": lambda n, loc: f"https://www.quickpeoplesearch.com/name/{n.lower().replace(' ', '-')}__{loc['city'].lower().replace(' ', '-')}",
        "selectors": ["a[href*='/details/']"],
        "prefix": "https://www.quickpeoplesearch.com",
    },
    {
        "name": "AdvancedCheck",
        "url": lambda n, loc: f"https://www.advancedbackgroundcheck.com/search?q={quote_plus(n)}+{quote_plus(loc['city'])}",
        "selectors": ["a[href*='/results/']"],
        "prefix": "https://www.advancedbackgroundcheck.com",
    },
    {
        "name": "CriminalWatchdog",
        "url": lambda n, loc: f"https://www.criminalwatchdog.com/search?q={quote_plus(n)}&location={quote_plus(loc['city'])}",
        "selectors": ["a[href*='/record/']"],
        "prefix": "https://www.criminalwatchdog.com",
    },
    {
        "name": "CyberChecks",
        "url": lambda n, loc: f"https://www.cyberbackgroundchecks.com/search?q={quote_plus(n)}+{quote_plus(loc['city'])}",
        "selectors": ["a[href*='/person/']"],
        "prefix": "https://www.cyberbackgroundchecks.com",
    },
    {
        "name": "Whitepages",
        "url": lambda n, loc: f"https://www.whitepages.com/name/{n.lower().replace(' ', '-')}/{loc['city'].lower().replace(' ', '-')}",
        "selectors": ["a[href*='/person/']"],
        "prefix": "https://www.whitepages.com",
    },
    {
        "name": "PeekYou",
        "url": lambda n, loc: f"https://www.peekyou.com/{quote_plus(n)}/{quote_plus(loc['city'])}",
        "selectors": ["a[href*='/peekyou/']"],
        "prefix": "https://www.peekyou.com",
    },
    {
        "name": "Radaris",
        "url": lambda n, loc: "https://radaris.com/ng/search?q=" + quote_plus(n + " " + loc["city"]),
        "selectors": ["a[href*='/p/']"],
        "prefix": "https://radaris.com",
    },
    {
        "name": "ThatsThem",
        "url": lambda n, loc: f"https://thatsthem.com/name/{quote_plus(n)}/{loc['city'].lower().replace(' ', '-')}",
        "selectors": ["a[href*='/person/']"],
        "prefix": "https://thatsthem.com",
    },
    {
        "name": "Nuwber",
        "url": lambda n, loc: f"https://nuwber.com/search?name={quote_plus(n)}&city={quote_plus(loc['city'])}",
        "selectors": ["a[href*='/person/']"],
        "prefix": "https://nuwber.com",
    },
    {
        "name": "ZabaSearch",
        "url": lambda n, loc: f"https://www.zabasearch.com/people/{quote_plus(n)}+{quote_plus(loc['city'])}",
        "selectors": ["a[href*='/people/']"],
        "prefix": "",
    },
    {
        "name": "CheckPeople",
        "url": lambda n, loc: f"https://checkpeople.com/search?q={quote_plus(n)}+{quote_plus(loc['city'])}",
        "selectors": ["a[href*='/person/']"],
        "prefix": "",
    },
    {
        "name": "Xlek",
        "url": lambda n, loc: f"https://www.xlek.com/search?q={quote_plus(n)}",
        "selectors": ["a[href*='/person/']"],
        "prefix": "https://www.xlek.com",
    },
    {
        "name": "Homemetry",
        "url": lambda n, loc: "https://homemetry.com/search?q=" + quote_plus(n + " " + loc["city"]),
        "selectors": ["a[href*='/property/']"],
        "prefix": "",
    },
]

# ---------------------------------------------------------------------------
# Canadian broker list
# ---------------------------------------------------------------------------
# NOTE: direct-scrape selectors below were verified against live pages on
# 2026-07-11 (canada411 routes person results to /bus/... links; whitepages.ca
# uses /person/ and /people/). They are best-effort — if a site's markup
# changes, the site is silently skipped (no false-positive links). A
# real-Facebook-export / real-CA-name validation pass is still required
# (see TIMELINE.md Gate T1-1 TODO: run end-to-end against REAL data).
# yellowpages.ca is intentionally excluded: it is a business directory and
# returns business listings, not people-search results.

CA_PHASE_1_SITES = [
    {
        "name": "Canada411",
        "broker_name": "canada411.ca",
        "url": lambda n, loc: f"https://www.canada411.ca/search/?what={quote_plus(n)}&where={quote_plus(loc['city'] + ' ' + loc['province']).strip()}",
        "selectors": ["a[href*='/bus/']", "a[href*='/person/']", "a[href*='/people/']"],
        "prefix": "https://www.canada411.ca",
    },
    {
        "name": "WhitepagesCA",
        "broker_name": "whitepages.ca",
        "url": lambda n, loc: f"https://www.whitepages.ca/search?name={quote_plus(n)}&location={quote_plus(loc['city'] + ' ' + loc['province']).strip()}",
        "selectors": ["a[href*='/person/']", "a[href*='/people/']"],
        "prefix": "https://www.whitepages.ca",
    },
]

# ---------------------------------------------------------------------------
# Free-tier teaser brokers (5 high-recognition US aggregators).
# The user-facing freemium flow scans ONLY these for free; the remaining
# 14 US brokers + 2 CA brokers are unlocked after the $19 one-time payment.
# ---------------------------------------------------------------------------
FREE_TIER_SITES = [s for s in PHASE_1_SITES if s["name"] in (
    "TruePeopleSearch", "FastPeopleSearch", "PeopleSearchNow",
    "FamilyTreeNow", "Whitepages",
)]

# Domains surfaced by the DuckDuckGo discovery pass. Canadian brokers added
# here so they get captured when they appear in search results.
DISCOVERY_DOMAINS = [
    "truepeople", "fastpeople", "peoplesearchnow", "whitepages",
    "peekyou", "radaris", "thatsthem", "familytreenow",
    "searchpeoplefree", "nuwber", "usphonebook",
    "advancedbackgroundcheck", "criminalwatchdog",
    "quickpeoplesearch", "checkpeople", "cyberbackground",
    "xlek", "homemetry", "zabasearch",
    "canada411", "whitepages.ca",
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


def _broker_name_for(site: dict, url: str) -> str:
    if site.get("broker_name"):
        return site["broker_name"]
    return url.split("/")[2].replace("www.", "")


async def run_scan(client_id: str, full_name: str, past_city: str, tier: str = "full") -> dict:
    """Run the data-broker scan.

    tier="free"  -> only the 5 FREE_TIER_SITES (cheap teaser, pre-payment)
    tier="full"  -> all US PHASE_1_SITES, plus CA_PHASE_1_SITES when the
                    location resolves to Canada (post-payment full report)
    """
    all_targets = []
    loc = parse_location(past_city)
    is_ca = loc["country"] == "CA"

    if tier == "free":
        sites = FREE_TIER_SITES
    else:
        # full: US location -> all 19 US brokers; CA location -> 2 CA brokers
        sites = CA_PHASE_1_SITES if is_ca else PHASE_1_SITES

    # Search query includes province when known (helps CA discovery).
    if loc["province"]:
        search_query = f'"{full_name}" "{loc["city"]}, {loc["province"]}"'
    else:
        search_query = f'"{full_name}" "{loc["city"]}"'

    brightdata_proxy_url = os.environ.get("BRIGHTDATA_PROXY")
    brightdata_proxy_cfg = None
    if brightdata_proxy_url and "@" in brightdata_proxy_url:
        parts = brightdata_proxy_url.split("@")
        creds, server = parts[0].replace("http://", ""), parts[1]
        user, pw = creds.split(":", 1)
        brightdata_proxy_cfg = {"server": f"http://{server}", "username": user, "password": pw}

    for attempt in range(1, 3):
        proxy_cfg = brightdata_proxy_cfg if attempt == 2 else None
        tag = "brightdata" if proxy_cfg else "direct"
        print(f"\n=== Attempt {attempt}/2 ({tag}) for {full_name} [{loc['city']}, {loc['province'] or 'n/a'} / {loc['country'] or 'unknown'}] ===")

        try:
            async with async_playwright() as p:
                # De-Google the bundled Chromium: kill Google telemetry /
                # account / safe-browsing / translate / variations and block
                # any outbound calls to Google endpoints at the network layer.
                # Chromium != Google Chrome, but it still ships Google service
                # code paths; these flags silence them. The request interceptor
                # below is the real guarantee — nothing leaves for Google.
                launch_args = {
                    "headless": True,
                    "args": [
                        "--no-sandbox", "--disable-setuid-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--ignore-certificate-errors",
                        # --- de-Google flags ---
                        "--disable-features=Translate,OptimizationHints,"
                        "MediaRouter,ChromeVariations,ChromeDeveloperSubmitFlag,"
                        "AccountConsistency,ConsistencyCheck,GoogleNowIntegration,"
                        "PreconnectToGoogleCom,PrivacySandboxSettings4,"
                        "SafeBrowsingEnhanced,AutofillServerCommunication,"
                        "PasswordLeakDetection,OptimizeLearning,InterestFeedContentSuggestions",
                        "--disable-background-networking",
                        "--disable-component-update",
                        "--disable-default-apps",
                        "--disable-domain-reliability",
                        "--disable-sync",
                        "--no-pings",
                        "--disable-preconnect",
                        "--safebrowsing-disable-auto-update",
                        "--disable-client-side-phishing-detection",
                        "--disable-dns-over-https",
                        "--disable-features=Gaia,AccountIdMigration,AccountReauthentication,"
                        "SecondaryAccountInfo,AccountCapabilities,ParentPermission,"
                        "PrivacySandboxAdsAPIs,TrustTokens,ConversionMeasurement,FedCm",
                    ]
                }
                if proxy_cfg:
                    launch_args["proxy"] = proxy_cfg
                print(f"proxy: {tag}")

                browser = await p.chromium.launch(**launch_args)
                context = await browser.new_context(
                    ignore_https_errors=True,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="en-CA" if is_ca else "en-US",
                )
                page = await context.new_page()

                # Network-layer guarantee: abort any request to Google-owned
                # hosts so nothing leaks to Google even if a flag is missed.
                _GOOGLE_SUFFIXES = (
                    "google.com", "google.ca", "gstatic.com", "googleapis.com",
                    "googletagmanager.com", "google-analytics.com", "gvt1.com",
                    "gmail.com", "googleusercontent.com", "youtube.com",
                    "accounts.google.com", "chromium.org",
                )

                async def _block_google(route):
                    host = (urlparse(route.request.url).netloc or "").lower()
                    if any(host == s or host.endswith("." + s) for s in _GOOGLE_SUFFIXES):
                        await route.abort()
                    else:
                        await route.continue_()

                await context.route("**/*", _block_google)

                # ---- DuckDuckGo search ----
                try:
                    print("  DuckDuckGo  search...", end=" ")
                    await page.goto(
                        f"https://html.duckduckgo.com/html/?q={quote_plus(search_query)}",
                            timeout=60000, wait_until="domcontentloaded"
                    )
                    await page.wait_for_timeout(2000)
                    page_text = await page.inner_text("body")
                    if "captcha" in page_text.lower():
                        print(f"DDG captcha")
                    elif len(page_text) < 200:
                        print(f"DDG short page ({len(page_text)} chars): {page_text[:100]}")
                    results = await page.query_selector_all("a.result__a")
                    found = 0
                    for r in results:
                        try:
                            href = await r.get_attribute("href")
                            title = await r.inner_text()
                            url = extract_url(href or "")
                            if url and any(d in url for d in DISCOVERY_DOMAINS):
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

                # ---- Direct broker scraping ----
                for site in sites:
                    name = site["name"]
                    if any(t.get("broker_name", "").replace("www.", "") in name.lower()
                           or name.lower() in t.get("broker_name", "").lower()
                           for t in all_targets):
                        continue

                    url = site["url"](full_name, loc)
                    try:
                        resp = await page.goto(url, timeout=60000, wait_until="domcontentloaded")
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
                                            "broker_name": _broker_name_for(site, full),
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
                            print(f"  {name:20s} no matches")

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

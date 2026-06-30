import aiohttp
import asyncio
import random
from typing import Optional

PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
]

async def fetch_proxies_from_source(url: str) -> list:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    text = await response.text()
                    proxies = [f"http://{line.strip()}" for line in text.split('\n') if line.strip()]
                    return proxies
    except Exception as e:
        print(f"[!] Failed to fetch from {url}: {e}")
    return []

async def fetch_all_proxies() -> list:
    tasks = [fetch_proxies_from_source(url) for url in PROXY_SOURCES]
    results = await asyncio.gather(*tasks)
    
    all_proxies = []
    for proxies in results:
        all_proxies.extend(proxies)
    
    # Remove duplicates and shuffle
    all_proxies = list(set(all_proxies))
    random.shuffle(all_proxies)
    
    return all_proxies

async def test_proxy(proxy: str) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://httpbin.org/ip",
                proxy=proxy,
                timeout=5
            ) as response:
                return response.status == 200
    except:
        return False

async def get_working_proxy(max_attempts: int = 30) -> Optional[str]:
    print("[+] Fetching free proxies...")
    proxies = await fetch_all_proxies()
    print(f"[+] Fetched {len(proxies)} free proxies")
    
    for i, proxy in enumerate(proxies[:max_attempts], 1):
        if await test_proxy(proxy):
            print(f"[+] Working proxy found: {proxy} (tried {i}/{max_attempts})")
            return proxy
    
    print("[!] No working proxy found")
    return None
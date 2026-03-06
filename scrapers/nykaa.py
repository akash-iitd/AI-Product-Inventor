"""
Nykaa review scraper.
PRIMARY: Uses SerpAPI Google Search (site:nykaa.com).
FALLBACK: Direct scraping with BeautifulSoup.
"""

import asyncio
import os
import random
import re
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]
BASE_URL = "https://www.nykaa.com"


async def _serpapi_search_nykaa(client, category):
    params = {"engine": "google", "q": f"site:nykaa.com {category} reviews", "gl": "in", "hl": "en", "num": 10, "api_key": SERPAPI_KEY}
    try:
        resp = await client.get("https://serpapi.com/search.json", params=params, timeout=20)
        if resp.status_code != 200: return []
        products = []
        for r in resp.json().get("organic_results", []):
            if "nykaa.com" in r.get("link", ""):
                products.append({"url": r["link"], "title": r.get("title", "").replace(" - Buy", "").replace("| Nykaa", "").strip(), "snippet": r.get("snippet", ""), "rating": 0})
        print(f"[Nykaa/SerpAPI] Found {len(products)} results")
        return products
    except Exception as e:
        print(f"[Nykaa/SerpAPI] Search error: {e}")
        return []


async def _serpapi_get_nykaa_reviews(client, product):
    reviews = []
    params = {"engine": "google", "q": f'site:nykaa.com "{product.get("title", "")}" review problem', "gl": "in", "num": 8, "api_key": SERPAPI_KEY}
    try:
        resp = await client.get("https://serpapi.com/search.json", params=params, timeout=20)
        if resp.status_code != 200: return reviews
        for r in resp.json().get("organic_results", []):
            snippet = r.get("snippet", "")
            if snippet and len(snippet) > 30:
                reviews.append({"source": "Nykaa", "product": product.get("title", ""), "rating": 0, "title": r.get("title", ""), "body": snippet, "date": "", "verified": True, "helpful": ""})
    except Exception: pass
    return reviews


async def _scrape_via_serpapi(category):
    async with httpx.AsyncClient(follow_redirects=True) as client:
        products = await _serpapi_search_nykaa(client, category)
        if not products: return []
        all_reviews = []
        for p in products[:5]:
            reviews = await _serpapi_get_nykaa_reviews(client, p)
            all_reviews.extend(reviews)
            await asyncio.sleep(0.3)
        for p in products:
            if p.get("snippet") and len(p["snippet"]) > 30:
                all_reviews.append({"source": "Nykaa", "product": p["title"], "rating": 0, "title": "", "body": p["snippet"], "date": "", "verified": True, "helpful": ""})
        print(f"[Nykaa/SerpAPI] Total reviews: {len(all_reviews)}")
        return all_reviews


def _get_headers():
    return {"User-Agent": random.choice(USER_AGENTS), "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "DNT": "1"}


async def _direct_search_products(client, category, max_products=5):
    try:
        resp = await client.get(f"{BASE_URL}/search/result/", params={"q": category}, headers=_get_headers(), timeout=15)
        if resp.status_code != 200: return []
        soup = BeautifulSoup(resp.text, "lxml")
        products = []
        for a in soup.select("a[href*='/p/']")[:max_products]:
            href = a.get("href", "")
            if "/p/" in href:
                url = href if href.startswith("http") else BASE_URL + href
                products.append({"url": url, "title": a.get_text(strip=True)[:100]})
        print(f"[Nykaa/Direct] Found {len(products)} products")
        return products
    except Exception as e:
        print(f"[Nykaa/Direct] Search error: {e}")
        return []


async def _direct_get_reviews(client, product):
    reviews = []
    try:
        await asyncio.sleep(random.uniform(1.0, 2.0))
        resp = await client.get(product["url"], headers=_get_headers(), timeout=15)
        if resp.status_code != 200: return []
        soup = BeautifulSoup(resp.text, "lxml")
        for block in soup.select("[class*='review'], [class*='Review']"):
            try:
                body_el = block.select_one("[class*='content'], [class*='text'], p")
                body = body_el.get_text(strip=True) if body_el else ""
                if body and len(body) > 20:
                    reviews.append({"source": "Nykaa", "product": product.get("title", ""), "rating": 0, "title": "", "body": body, "date": "", "verified": True, "helpful": ""})
            except Exception: continue
    except Exception: pass
    return reviews


async def _scrape_direct(category):
    async with httpx.AsyncClient(follow_redirects=True) as client:
        products = await _direct_search_products(client, category, 4)
        if not products: return []
        all_reviews = []
        for p in products:
            reviews = await _direct_get_reviews(client, p)
            all_reviews.extend(reviews)
            await asyncio.sleep(random.uniform(0.5, 1.0))
        print(f"[Nykaa/Direct] Total reviews: {len(all_reviews)}")
        return all_reviews


async def scrape_nykaa_reviews(category: str, region: str = "India") -> List[Dict]:
    print(f"[Nykaa] Starting scrape for category: {category}")
    if SERPAPI_KEY:
        reviews = await _scrape_via_serpapi(category)
        if reviews: return reviews
    print("[Nykaa] Using direct scraping (fallback)")
    return await _scrape_direct(category)

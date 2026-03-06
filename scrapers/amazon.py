"""
Amazon India review scraper.
PRIMARY: Uses SerpAPI for reliable, structured data.
FALLBACK: Direct scraping with BeautifulSoup when SerpAPI key is unavailable.
"""

import asyncio
import os
import random
import re
import json
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

BASE_URL = "https://www.amazon.in"


async def _serpapi_search_products(client, category, max_products=5):
    params = {"engine": "amazon", "amazon_domain": "amazon.in", "search_term": category, "api_key": SERPAPI_KEY}
    try:
        resp = await client.get("https://serpapi.com/search.json", params=params, timeout=20)
        if resp.status_code != 200: return []
        data = resp.json()
        products = []
        for r in data.get("organic_results", [])[:max_products]:
            products.append({"asin": r.get("asin", ""), "title": r.get("title", ""), "link": r.get("link", ""), "rating": r.get("rating", 0)})
        print(f"[Amazon/SerpAPI] Found {len(products)} products")
        return products
    except Exception as e:
        print(f"[Amazon/SerpAPI] Search error: {e}")
        return []


async def _serpapi_get_reviews(client, asin, product_title):
    reviews = []
    for star_filter in ["1_star", "2_star", "3_star"]:
        params = {"engine": "amazon_product", "product_id": asin, "amazon_domain": "amazon.in", "api_key": SERPAPI_KEY, "type": "reviews", "sort_by": "helpful", "star_rating": star_filter}
        try:
            resp = await client.get("https://serpapi.com/search.json", params=params, timeout=20)
            if resp.status_code != 200: continue
            for r in resp.json().get("reviews", []):
                body = r.get("body", "")
                if body and len(body) > 20:
                    reviews.append({"source": "Amazon India", "product": product_title, "rating": r.get("rating", 0), "title": r.get("title", ""), "body": body, "date": r.get("date", ""), "verified": r.get("verified_purchase", False), "helpful": r.get("helpful_count", "")})
            await asyncio.sleep(0.5)
        except Exception as e:
            continue
    return reviews


async def _scrape_via_serpapi(category):
    async with httpx.AsyncClient(follow_redirects=True) as client:
        products = await _serpapi_search_products(client, category)
        if not products: return []
        all_reviews = []
        for p in products:
            if p["asin"]:
                reviews = await _serpapi_get_reviews(client, p["asin"], p["title"])
                all_reviews.extend(reviews)
                await asyncio.sleep(0.3)
        print(f"[Amazon/SerpAPI] Total reviews: {len(all_reviews)}")
        return all_reviews


def _get_headers():
    return {"User-Agent": random.choice(USER_AGENTS), "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9,hi;q=0.8", "DNT": "1", "Connection": "keep-alive"}


async def _direct_search_products(client, category, max_products=5):
    try:
        resp = await client.get(f"{BASE_URL}/s", params={"k": category}, headers=_get_headers(), timeout=15)
        if resp.status_code != 200: return []
        soup = BeautifulSoup(resp.text, "lxml")
        links = []
        for card in soup.select('[data-component-type="s-search-result"]')[:max_products]:
            tag = card.select_one("h2 a")
            if tag and tag.get("href"):
                href = tag["href"] if tag["href"].startswith("http") else BASE_URL + tag["href"]
                links.append(href)
        print(f"[Amazon/Direct] Found {len(links)} products")
        return links
    except Exception as e:
        print(f"[Amazon/Direct] Search error: {e}")
        return []


def _extract_asin(url):
    match = re.search(r"/dp/([A-Z0-9]{10})", url)
    return match.group(1) if match else ""


async def _direct_get_reviews(client, product_url, max_pages=2):
    asin = _extract_asin(product_url)
    if not asin: return []
    reviews = []
    for page in range(1, max_pages + 1):
        try:
            await asyncio.sleep(random.uniform(1.0, 2.5))
            resp = await client.get(f"{BASE_URL}/product-reviews/{asin}", params={"pageNumber": str(page), "filterByStar": "critical", "sortBy": "helpful"}, headers=_get_headers(), timeout=15)
            if resp.status_code != 200: continue
            soup = BeautifulSoup(resp.text, "lxml")
            product_title = ""
            title_tag = soup.select_one("a[data-hook='product-link']")
            if title_tag: product_title = title_tag.get_text(strip=True)
            for div in soup.select('[data-hook="review"]'):
                try:
                    rating_tag = div.select_one('[data-hook="review-star-rating"] span, .a-icon-alt')
                    rating = 0
                    if rating_tag:
                        m = re.search(r"(\d+(\.\d+)?)", rating_tag.get_text(strip=True))
                        if m: rating = float(m.group(1))
                    body_tag = div.select_one('[data-hook="review-body"] span')
                    body = body_tag.get_text(strip=True) if body_tag else ""
                    title_tag2 = div.select_one('[data-hook="review-title"]')
                    title = title_tag2.get_text(strip=True) if title_tag2 else ""
                    if body and len(body) > 20:
                        reviews.append({"source": "Amazon India", "product": product_title, "rating": rating, "title": title, "body": body, "date": "", "verified": True, "helpful": ""})
                except Exception: continue
        except Exception as e:
            continue
    return reviews


async def _scrape_direct(category):
    async with httpx.AsyncClient(follow_redirects=True) as client:
        urls = await _direct_search_products(client, category)
        if not urls: return []
        all_reviews = []
        for url in urls:
            reviews = await _direct_get_reviews(client, url)
            all_reviews.extend(reviews)
            await asyncio.sleep(random.uniform(0.5, 1.5))
        print(f"[Amazon/Direct] Total reviews: {len(all_reviews)}")
        return all_reviews


async def scrape_amazon_reviews(category: str, region: str = "India") -> List[Dict]:
    print(f"[Amazon] Starting scrape for category: {category}")
    if SERPAPI_KEY:
        print("[Amazon] Using SerpAPI (primary)")
        reviews = await _scrape_via_serpapi(category)
        if reviews: return reviews
        print("[Amazon] SerpAPI returned no results, falling back to direct scraping")
    print("[Amazon] Using direct scraping (fallback)")
    return await _scrape_direct(category)

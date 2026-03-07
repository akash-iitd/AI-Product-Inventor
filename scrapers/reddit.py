"""
Reddit scraper / API integration.
Searches relevant subreddits for consumer complaints, product requests,
and DIY solutions that signal unmet needs.
"""

import asyncio
import os
import random
import re
import httpx
from typing import List, Dict

# Subreddit pools by category type
SUBREDDIT_MAP = {
    "default": [
        "IndianSkincareAddicts", "IndianBeautyDeals", "IndianMakeupAddicts",
        "india", "IndianFood", "bangalore", "mumbai", "delhi",
        "Fitness", "nutrition", "SkincareAddiction", "HaircareScience",
    ],
    "beauty": [
        "IndianSkincareAddicts", "IndianBeautyDeals", "IndianMakeupAddicts",
        "SkincareAddiction", "beauty", "MakeupAddiction", "AsianBeauty",
    ],
    "food": [
        "IndianFood", "food", "Cooking", "EatCheapAndHealthy",
        "nutrition", "MealPrepSunday", "india",
    ],
    "fitness": [
        "Fitness", "bodyweightfitness", "nutrition", "Supplements",
        "loseit", "india", "IndianSkincareAddicts",
    ],
    "tech": [
        "india", "IndianGaming", "mobilerepair", "gadgets",
        "technology", "Android", "apple",
    ],
    "baby": [
        "india", "Parenting", "NewParents", "BabyBumps",
        "beyondthebump", "Mommit",
    ],
    "wellness": [
        "IndianSkincareAddicts", "Ayurveda", "nutrition",
        "Supplements", "naturalliving", "india",
    ],
}


def _detect_category_type(category: str) -> str:
    """Detect which subreddit pool to use based on category keywords."""
    category_lower = category.lower()
    
    beauty_kw = ["skin", "hair", "beauty", "cream", "serum", "face", "moistur", "sunscreen", "acne", "cosmetic", "makeup", "nykaa", "lip", "nail"]
    food_kw = ["food", "snack", "protein", "bar", "drink", "beverage", "tea", "coffee", "health drink", "supplement", "vitamin", "organic"]
    fitness_kw = ["fitness", "workout", "gym", "protein", "supplement", "weight", "muscle", "exercise"]
    tech_kw = ["phone", "laptop", "earphone", "headphone", "gadget", "charger", "cable", "smart", "watch"]
    baby_kw = ["baby", "infant", "toddler", "diaper", "child", "kid", "parenting", "mother"]
    wellness_kw = ["wellness", "ayurved", "herbal", "natural", "essential oil", "meditation", "yoga"]

    for kw in beauty_kw:
        if kw in category_lower:
            return "beauty"
    for kw in food_kw:
        if kw in category_lower:
            return "food"
    for kw in fitness_kw:
        if kw in category_lower:
            return "fitness"
    for kw in tech_kw:
        if kw in category_lower:
            return "tech"
    for kw in baby_kw:
        if kw in category_lower:
            return "baby"
    for kw in wellness_kw:
        if kw in category_lower:
            return "wellness"
    
    return "default"


async def _scrape_reddit_web(category: str, subreddits: List[str], max_posts: int = 30) -> List[Dict]:
    """Scrape Reddit via old.reddit.com (no API key needed)."""
    posts = []
    
    search_queries = [
        f"{category} problem",
        f"{category} alternative",
        f"{category} recommendation",
        f"{category} complaint",
        f"{category} looking for",
        f"{category} wish",
        f"{category} India",
    ]

    async with httpx.AsyncClient(follow_redirects=True) as client:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        # Search across selected subreddits
        for subreddit in subreddits[:4]:
            for query in search_queries[:3]:
                if len(posts) >= max_posts:
                    break
                    
                try:
                    search_url = f"https://old.reddit.com/r/{subreddit}/search.json"
                    params = {
                        "q": query,
                        "restrict_sr": "on",
                        "sort": "relevance",
                        "t": "year",
                        "limit": 10,
                    }
                    
                    await asyncio.sleep(random.uniform(1.5, 3.0))
                    resp = await client.get(search_url, params=params, headers={
                        "User-Agent": "Invently/1.0 (research bot)",
                    }, timeout=15)
                    
                    if resp.status_code == 200:
                        try:
                            data = resp.json()
                            children = data.get("data", {}).get("children", [])
                            
                            for child in children:
                                post_data = child.get("data", {})
                                title = post_data.get("title", "")
                                selftext = post_data.get("selftext", "")
                                score = post_data.get("score", 0)
                                num_comments = post_data.get("num_comments", 0)
                                permalink = post_data.get("permalink", "")
                                created_utc = post_data.get("created_utc", 0)
                                subreddit_name = post_data.get("subreddit", subreddit)
                                
                                if title and (len(selftext) > 20 or score > 5):
                                    posts.append({
                                        "source": f"Reddit r/{subreddit_name}",
                                        "title": title,
                                        "body": selftext[:2000] if selftext else "",
                                        "score": score,
                                        "num_comments": num_comments,
                                        "url": f"https://reddit.com{permalink}" if permalink else "",
                                        "subreddit": subreddit_name,
                                    })
                        except Exception:
                            pass

                except Exception as e:
                    print(f"[Reddit] Error searching r/{subreddit}: {e}")
                    continue

    return posts[:max_posts]


async def _get_post_comments(client: httpx.AsyncClient, permalink: str, max_comments: int = 5) -> List[str]:
    """Get top comments from a Reddit post."""
    comments = []
    try:
        url = f"https://old.reddit.com{permalink}.json"
        resp = await client.get(url, headers={
            "User-Agent": "Invently/1.0 (research bot)",
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if len(data) > 1:
                comment_children = data[1].get("data", {}).get("children", [])
                for c in comment_children[:max_comments]:
                    body = c.get("data", {}).get("body", "")
                    if body and len(body) > 20:
                        comments.append(body[:500])
    except Exception:
        pass
    
    return comments


async def scrape_reddit_posts(category: str) -> List[Dict]:
    """
    Search Reddit for posts related to the category that reveal consumer needs.
    Returns list of post dicts with source, title, body, score, etc.
    """
    print(f"[Reddit] Starting scrape for category: {category}")
    
    cat_type = _detect_category_type(category)
    subreddits = SUBREDDIT_MAP.get(cat_type, SUBREDDIT_MAP["default"])
    print(f"[Reddit] Using subreddit pool: {cat_type} -> {subreddits[:5]}")
    
    posts = await _scrape_reddit_web(category, subreddits, max_posts=30)
    
    # Enrich top posts with comments
    if posts:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            for post in posts[:10]:  # Only enrich top 10
                if post.get("url") and "/comments/" in post["url"]:
                    permalink = post["url"].replace("https://reddit.com", "")
                    comments = await _get_post_comments(client, permalink)
                    post["top_comments"] = comments
                    await asyncio.sleep(random.uniform(1.0, 2.0))
    
    print(f"[Reddit] Total posts collected: {len(posts)}")
    return posts

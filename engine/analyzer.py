"""
Unified AI Analysis Engine — Single consolidated Gemini call for pain points + gaps.
Reduces API calls to stay within free tier limits.
No mock data — real results or explicit errors only.
"""

import asyncio
import json
import os
from typing import List, Dict, Tuple
from engine.gemini_helper import call_gemini

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


async def analyze_and_find_gaps(
    reviews: List[Dict],
    reddit_posts: List[Dict],
    trends_data: Dict,
    category: str,
) -> Tuple[List[Dict], List[Dict]]:
    """
    SINGLE Gemini call to extract pain points AND identify market gaps.
    Returns (pain_points, market_gaps) tuple.
    """
    print(f"[Engine] Analyzing {len(reviews)} reviews + {len(reddit_posts)} Reddit posts for '{category}'")

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is required. Set it in your .env file.")

    # Build review context (limit to ~30 most useful reviews)
    review_text = ""
    useful_reviews = [r for r in reviews if r.get("body") and len(r.get("body", "")) > 20][:30]
    for j, r in enumerate(useful_reviews):
        review_text += f"\nReview {j+1} [{r.get('source','?')}, {r.get('product','?')}, *{r.get('rating','?')}]: "
        if r.get("title"):
            review_text += f"{r['title']} -- "
        review_text += f"{r['body'][:300]}\n"

    # Build Reddit context (limit to top 20 by score)
    reddit_text = ""
    sorted_posts = sorted(reddit_posts, key=lambda p: p.get("score", 0), reverse=True)[:20]
    for j, post in enumerate(sorted_posts):
        reddit_text += f"\nReddit #{j+1} [r/{post.get('subreddit','?')}, score={post.get('score',0)}]: {post['title']}\n"
        if post.get("body"):
            reddit_text += f"  Body: {post['body'][:300]}\n"
        if post.get("top_comments"):
            for c in post["top_comments"][:2]:
                reddit_text += f"  Comment: {c[:150]}\n"

    # Build trends context
    trends_context = ""
    if trends_data:
        if trends_data.get("related_queries_rising"):
            trends_context += "Rising searches: " + ", ".join(
                f"\"{q['query']}\" (+{q['value']}%)" for q in trends_data["related_queries_rising"][:8]
            ) + "\n"
        if trends_data.get("related_queries_top"):
            trends_context += "Top searches: " + ", ".join(
                f"\"{q['query']}\" ({q['value']})" for q in trends_data["related_queries_top"][:8]
            ) + "\n"

    total_data = len(useful_reviews) + len(sorted_posts)
    if total_data == 0:
        raise ValueError(f"No consumer data collected for '{category}'. Try a different category.")

    prompt = f"""You are a consumer insights analyst for the Indian D2C market. Analyze ALL the data below for "{category}" and produce TWO outputs in a single JSON response.

=== CONSUMER DATA ({total_data} data points) ===

PRODUCT REVIEWS ({len(useful_reviews)} reviews):
{review_text if review_text.strip() else "(No product reviews available -- focus on Reddit data below)"}

REDDIT DISCUSSIONS ({len(sorted_posts)} posts):
{reddit_text if reddit_text.strip() else "(No Reddit data available -- focus on reviews above)"}

GOOGLE TRENDS:
{trends_context if trends_context.strip() else "(No trends data available)"}

=== YOUR TASK ===

Analyze this real consumer data and return a JSON object with TWO keys:

1. "pain_points" -- Array of 5-10 SPECIFIC consumer pain points. Focus on:
   - Specific functional complaints (what doesn't work)
   - Unmet needs (what people wish existed)
   - Workarounds/DIY hacks (STRONGEST signal of unmet need)
   - Quality gaps (where products fail expectations)
   - Missing alternatives ("I wish there was...")

   Each pain point must have:
   - "pain_point": Clear, specific description
   - "category": One of ["functionality","quality","price_value","availability","ingredients","side_effects","missing_feature","workaround"]
   - "severity": 1-5 (5 = most severe)
   - "frequency": Estimated mentions
   - "evidence": Array of 2-3 direct quotes from the data
   - "source_products": Array of products/brands mentioned
   - "consumer_hack": Workaround if described (null if none)

2. "market_gaps" -- Array of 3-5 MARKET GAPS. A gap = demand exists (pain points + trends prove it) but supply doesn't serve it.

   Each gap must have:
   - "gap_title": Specific name
   - "gap_description": 2-3 sentence opportunity description
   - "demand_signals": Array of evidence (pain points, search trends)
   - "current_supply_failure": Why existing products fail
   - "opportunity_size": "large"|"medium"|"small"
   - "trend_direction": "growing"|"stable"|"emerging"
   - "target_audience": Specific consumer segment
   - "confidence_score": 1-10

Return ONLY valid JSON with keys "pain_points" and "market_gaps". No markdown, no explanation."""

    result = await call_gemini(prompt)

    if result and isinstance(result, dict):
        pain_points = result.get("pain_points", [])
        gaps = result.get("market_gaps", [])
        if isinstance(pain_points, list) and isinstance(gaps, list):
            print(f"[Engine] SUCCESS: Extracted {len(pain_points)} pain points and {len(gaps)} market gaps")
            return pain_points, gaps

    raise ValueError("Gemini API failed to analyze the data. Please try again in a minute (rate limit may have reset).")

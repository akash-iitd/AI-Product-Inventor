"""
Google Trends integration using pytrends.
Fetches trending search queries, related topics, and interest-over-time data
to validate consumer demand signals.
"""

import asyncio
from typing import Dict, List
from pytrends.request import TrendReq


async def get_google_trends(category: str, region: str = "India") -> Dict:
    """
    Fetch Google Trends data for a category.
    Returns dict with interest_over_time, related_queries, and related_topics.
    """
    print(f"[Trends] Fetching Google Trends for: {category}")
    
    # Run in executor since pytrends is synchronous
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _fetch_trends, category, region)
    return result


def _fetch_trends(category: str, region: str) -> Dict:
    """Synchronous trends fetching."""
    try:
        geo = "IN" if region.lower() == "india" else ""
        pytrends = TrendReq(hl="en-US", tz=330, timeout=(10, 25))
        
        # Build payload
        keywords = [category]
        pytrends.build_payload(keywords, cat=0, timeframe="today 12-m", geo=geo)
        
        result = {
            "keyword": category,
            "interest_over_time": [],
            "related_queries_top": [],
            "related_queries_rising": [],
            "related_topics_top": [],
            "related_topics_rising": [],
            "suggestions": [],
        }
        
        # Interest over time
        try:
            iot = pytrends.interest_over_time()
            if not iot.empty:
                for date, row in iot.iterrows():
                    result["interest_over_time"].append({
                        "date": str(date.date()),
                        "interest": int(row[category]) if category in row else 0,
                    })
        except Exception as e:
            print(f"[Trends] Interest over time error: {e}")
        
        # Related queries
        try:
            related = pytrends.related_queries()
            if category in related:
                top_df = related[category].get("top")
                if top_df is not None and not top_df.empty:
                    for _, row in top_df.head(15).iterrows():
                        result["related_queries_top"].append({
                            "query": row.get("query", ""),
                            "value": int(row.get("value", 0)),
                        })
                
                rising_df = related[category].get("rising")
                if rising_df is not None and not rising_df.empty:
                    for _, row in rising_df.head(15).iterrows():
                        result["related_queries_rising"].append({
                            "query": row.get("query", ""),
                            "value": int(row.get("value", 0)),
                        })
        except Exception as e:
            print(f"[Trends] Related queries error: {e}")
        
        # Related topics
        try:
            topics = pytrends.related_topics()
            if category in topics:
                top_topics = topics[category].get("top")
                if top_topics is not None and not top_topics.empty:
                    for _, row in top_topics.head(10).iterrows():
                        result["related_topics_top"].append({
                            "title": row.get("topic_title", ""),
                            "type": row.get("topic_type", ""),
                            "value": int(row.get("value", 0)),
                        })
                
                rising_topics = topics[category].get("rising")
                if rising_topics is not None and not rising_topics.empty:
                    for _, row in rising_topics.head(10).iterrows():
                        result["related_topics_rising"].append({
                            "title": row.get("topic_title", ""),
                            "type": row.get("topic_type", ""),
                            "value": int(row.get("value", 0)),
                        })
        except Exception as e:
            print(f"[Trends] Related topics error: {e}")
        
        # Search suggestions
        try:
            suggestions = pytrends.suggestions(keyword=category)
            result["suggestions"] = [
                {"title": s.get("title", ""), "type": s.get("type", "")}
                for s in suggestions[:10]
            ]
        except Exception as e:
            print(f"[Trends] Suggestions error: {e}")
        
        print(f"[Trends] Got {len(result['interest_over_time'])} time points, "
              f"{len(result['related_queries_top'])} top queries, "
              f"{len(result['related_queries_rising'])} rising queries")
        
        return result
        
    except Exception as e:
        print(f"[Trends] Error: {e}")
        return {
            "keyword": category,
            "interest_over_time": [],
            "related_queries_top": [],
            "related_queries_rising": [],
            "related_topics_top": [],
            "related_topics_rising": [],
            "suggestions": [],
            "error": str(e),
        }

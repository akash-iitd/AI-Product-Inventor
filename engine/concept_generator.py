"""
Unified Concept Generator + Scorer — Single Gemini call.
Generates product concepts AND scores them in one shot.
No mock data — real results or explicit errors only.
"""

import asyncio
import json
import os
from typing import List, Dict
from engine.gemini_helper import call_gemini

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


async def generate_and_score_concepts(
    gaps: List[Dict],
    pain_points: List[Dict],
    trends_data: Dict,
    category: str,
) -> List[Dict]:
    """
    SINGLE Gemini call to generate concepts AND score them.
    Returns fully scored concept list.
    """
    print(f"[ConceptGen] Generating + scoring concepts for {len(gaps)} gaps in '{category}'")

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is required.")

    # Summarize trends
    trending = []
    if trends_data.get("related_queries_rising"):
        trending = [f"{q['query']} (+{q['value']}%)" for q in trends_data["related_queries_rising"][:6]]
    top_queries = []
    if trends_data.get("related_queries_top"):
        top_queries = [q["query"] for q in trends_data["related_queries_top"][:5]]

    prompt = f"""You are a D2C product innovation strategist. Generate product concepts for "{category}" based on validated market data.

== MARKET GAPS (proven by real consumer data) ==
{json.dumps(gaps, indent=2)}

== TOP CONSUMER PAIN POINTS ==
{json.dumps(pain_points[:8], indent=2)}

== TRENDING SEARCHES IN INDIA ==
Rising: {', '.join(trending) if trending else 'N/A'}
Top: {', '.join(top_queries) if top_queries else 'N/A'}

== INSTRUCTIONS ==
Generate 5-8 innovative product concepts. Each must:
- Be NOVEL, not a copy of existing products
- Target the INDIAN MARKET specifically
- Address specific pain points with cited evidence
- Be realistic for a D2C brand

For EACH concept, also SCORE it on 5 dimensions (0-100):
- market_size: How many consumers need this?
- competition: How uncrowded? (100 = no competition)
- consumer_urgency: How desperately wanted?
- trend_momentum: Is demand growing?
- feasibility: How realistic to build?

Return a JSON array. Each item must have:
- "concept_name": Creative product name
- "tagline": One-line value prop (max 10 words)
- "description": 3-4 sentence description
- "target_audience": Specific demographics + psychographics
- "key_features": Array of 4-6 features
- "differentiator": What makes it unique (specific)
- "evidence": {{"pain_points_solved": [...], "consumer_quotes": ["quote1","quote2"], "trend_signals": [...]}}
- "price_range": INR range string
- "go_to_market": 2-3 sentence strategy
- "innovation_type": "breakthrough"|"improvement"|"adaptation"|"new_category"
- "scores": {{"market_size": N, "competition": N, "consumer_urgency": N, "trend_momentum": N, "feasibility": N}}
- "overall_score": Weighted avg (market*0.25 + competition*0.2 + urgency*0.25 + trends*0.15 + feasibility*0.15)
- "verdict": "Strong Opportunity"|"Worth Exploring"|"Weak Signal"
- "score_rationale": One sentence explaining score
- "risk_factors": Array of 1-2 key risks

Sort by overall_score descending. Return ONLY valid JSON array, no markdown."""

    result = await call_gemini(prompt)

    if result and isinstance(result, list) and len(result) > 0:
        # Sort by overall_score
        result.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
        print(f"[ConceptGen] SUCCESS: Generated {len(result)} scored concepts. Top: {result[0].get('overall_score', '?')}")
        return result

    raise ValueError("Gemini API failed to generate concepts. Please try again in a minute.")

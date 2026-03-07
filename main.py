"""
Invently — FastAPI Backend
Scans product reviews, forums, and trends to identify genuine unmet consumer needs
and generates data-backed product concepts.

Pipeline: 2 Gemini API calls total (optimized for free tier).
Call 1: Analyze data → pain points + market gaps
Call 2: Generate + score product concepts
"""

import asyncio
import os
import uuid
import json
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from scrapers.amazon import scrape_amazon_reviews
from scrapers.flipkart import scrape_flipkart_reviews
from scrapers.nykaa import scrape_nykaa_reviews
from scrapers.reddit import scrape_reddit_posts
from scrapers.trends import get_google_trends
from engine.analyzer import analyze_and_find_gaps
from engine.concept_generator import generate_and_score_concepts

app = FastAPI(title="Invently", version="1.0.0")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# In-memory job store
jobs: dict = {}


class AnalyzeRequest(BaseModel):
    category: str
    region: str = "India"


class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str
    result: Optional[dict] = None


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.post("/api/analyze")
async def start_analysis(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Job created, starting analysis...",
        "result": None,
        "created_at": datetime.now().isoformat(),
        "category": request.category,
        "region": request.region,
    }
    background_tasks.add_task(run_pipeline, job_id, request.category, request.region)
    return {"job_id": job_id, "status": "pending"}


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "message": job["message"],
    }


@app.get("/api/results/{job_id}")
async def get_results(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    if job["status"] != "complete":
        return {
            "job_id": job_id,
            "status": job["status"],
            "message": job["message"],
            "result": None,
        }
    return {
        "job_id": job_id,
        "status": "complete",
        "result": job["result"],
    }


async def run_pipeline(job_id: str, category: str, region: str):
    """
    Run the full analysis pipeline in background.
    Total Gemini calls: exactly 2 (optimized for free tier).
    """
    try:
        # ── Step 1: Scrape data from all sources ──
        jobs[job_id].update({"status": "scraping", "progress": 5, "message": "Scraping product reviews from Amazon..."})
        
        # Run scrapers with error tolerance
        amazon_reviews = []
        flipkart_reviews = []
        nykaa_reviews = []
        
        try:
            amazon_reviews = await scrape_amazon_reviews(category, region)
        except Exception as e:
            print(f"[Pipeline] Amazon scraper error (non-fatal): {e}")
        jobs[job_id].update({"progress": 15, "message": f"Amazon: {len(amazon_reviews)} reviews. Scraping Flipkart..."})
        
        try:
            flipkart_reviews = await scrape_flipkart_reviews(category, region)
        except Exception as e:
            print(f"[Pipeline] Flipkart scraper error (non-fatal): {e}")
        jobs[job_id].update({"progress": 22, "message": f"Flipkart: {len(flipkart_reviews)} reviews. Scraping Nykaa..."})
        
        try:
            nykaa_reviews = await scrape_nykaa_reviews(category, region)
        except Exception as e:
            print(f"[Pipeline] Nykaa scraper error (non-fatal): {e}")
        jobs[job_id].update({"progress": 30, "message": f"Nykaa: {len(nykaa_reviews)} reviews. Scanning Reddit..."})
        
        reddit_posts = []
        try:
            reddit_posts = await scrape_reddit_posts(category)
        except Exception as e:
            print(f"[Pipeline] Reddit scraper error (non-fatal): {e}")
        jobs[job_id].update({"progress": 40, "message": f"Reddit: {len(reddit_posts)} posts. Fetching Google Trends..."})
        
        trends_data = {}
        try:
            trends_data = await get_google_trends(category, region)
        except Exception as e:
            print(f"[Pipeline] Trends error (non-fatal): {e}")
        jobs[job_id].update({"progress": 48, "message": "All data collected. Starting AI analysis..."})

        all_reviews = amazon_reviews + flipkart_reviews + nykaa_reviews
        total_data = len(all_reviews) + len(reddit_posts)
        
        if total_data == 0:
            jobs[job_id].update({
                "status": "error",
                "message": f"Could not collect any consumer data for '{category}'. All scrapers were blocked. Try a different category or try again later.",
            })
            return

        # ── Step 2: GEMINI CALL 1 — Analyze data → pain points + gaps ──
        jobs[job_id].update({
            "status": "analyzing",
            "progress": 52,
            "message": f"Analyzing {total_data} data points with Gemini AI... (this may take 30-60s)"
        })
        
        pain_points, gaps = await analyze_and_find_gaps(all_reviews, reddit_posts, trends_data, category)
        
        jobs[job_id].update({
            "progress": 72,
            "message": f"Found {len(pain_points)} pain points, {len(gaps)} market gaps. Generating product concepts..."
        })
        
        # ── Step 3: GEMINI CALL 2 — Generate + score concepts ──
        jobs[job_id].update({
            "status": "generating",
            "progress": 75,
            "message": "Generating and scoring product concepts with Gemini AI... (this may take 30-60s)"
        })
        
        scored_concepts = await generate_and_score_concepts(gaps, pain_points, trends_data, category)
        
        # ── Done ──
        result = {
            "category": category,
            "region": region,
            "data_summary": {
                "total_reviews": len(all_reviews),
                "reddit_posts": len(reddit_posts),
                "total_data_points": total_data,
            },
            "pain_points": pain_points,
            "market_gaps": gaps,
            "concepts": scored_concepts,
            "trends": trends_data,
            "generated_at": datetime.now().isoformat(),
        }
        
        jobs[job_id].update({
            "status": "complete",
            "progress": 100,
            "message": f"Analysis complete! {len(pain_points)} pain points, {len(gaps)} gaps, {len(scored_concepts)} concepts.",
            "result": result,
        })
        
    except ValueError as e:
        # Expected errors (no data, API failures)
        jobs[job_id].update({
            "status": "error",
            "message": str(e),
        })
    except Exception as e:
        jobs[job_id].update({
            "status": "error",
            "message": f"Unexpected error: {str(e)}. Please try again.",
        })
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# AI Product Inventor

AI-powered system that identifies genuine unmet consumer needs by analyzing live data from Reddit, Google Trends, and product reviews, then generates data-backed product concepts.

## Features

- **Live Data Collection** — Scrapes Reddit, Amazon, Flipkart, Nykaa, and Google Trends
- **AI Pain Point Extraction** — Uses Gemini 2.5 Flash to find real consumer frustrations
- **Market Gap Analysis** — Identifies where demand exists but supply fails
- **Product Concept Generation** — Creates novel, scored product ideas backed by evidence
- **Premium Dark UI** — Glassmorphism design with radar charts and animated transitions

## Architecture

```
Pipeline: Only 2 Gemini API calls (optimized for free tier)

Scrape Data (Reddit + Trends + Reviews)
    |
    v
Gemini Call 1: Analyze → Pain Points + Market Gaps
    |
    v
Gemini Call 2: Generate + Score Product Concepts
    |
    v
Premium UI with tabs, charts, evidence
```

## Tech Stack

- **Backend**: FastAPI + Python
- **AI**: Google Gemini 2.5 Flash
- **Scrapers**: httpx, BeautifulSoup, SerpAPI (optional)
- **Trends**: pytrends (Google Trends)
- **Frontend**: Vanilla HTML/CSS/JS + Chart.js

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your GEMINI_API_KEY to .env
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `SERPAPI_KEY` | No | SerpAPI key for e-commerce reviews |

## License

MIT

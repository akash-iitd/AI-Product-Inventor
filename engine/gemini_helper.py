"""
Shared Gemini API helper — fast, with smart retry.
Only 2 calls per pipeline, so minimal rate limiting needed.
"""

import asyncio
import json
import os
import re
import time

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Model to use
MODELS = [
    "gemini-2.5-flash",
]

# Minimal rate limiter — just 2s gap since we only make 2 calls
_last_call_time = 0
_MIN_DELAY = 2.0


async def call_gemini(prompt: str, max_retries: int = 2) -> dict | list | None:
    """
    Call Gemini API. Fast path: no retry delay if first call succeeds.
    On 429: try next model immediately instead of waiting.
    """
    global _last_call_time

    if not GEMINI_API_KEY:
        print("  [Gemini] No API key configured")
        return None

    try:
        from google import genai
    except ImportError:
        print("  [Gemini] google-genai not installed")
        return None

    client = genai.Client(api_key=GEMINI_API_KEY)

    for model_name in MODELS:
        for attempt in range(max_retries):
            # Brief delay between calls
            now = time.time()
            elapsed = now - _last_call_time
            if elapsed < _MIN_DELAY:
                await asyncio.sleep(_MIN_DELAY - elapsed)

            _last_call_time = time.time()

            try:
                print(f"  [Gemini] Calling {model_name}...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )

                text = response.text.strip()
                # Strip markdown code fences
                if text.startswith("```"):
                    text = re.sub(r"^```\w*\n?", "", text)
                    text = re.sub(r"\n?```$", "", text)
                    text = text.strip()

                result = json.loads(text)
                print(f"  [Gemini] SUCCESS with {model_name}")
                return result

            except json.JSONDecodeError:
                # Try to extract JSON from messy response
                if text:
                    for pattern in [r'\[[\s\S]*\]', r'\{[\s\S]*\}']:
                        match = re.search(pattern, text)
                        if match:
                            try:
                                return json.loads(match.group())
                            except:
                                pass
                print(f"  [Gemini] JSON parse failed on {model_name}, retrying...")
                continue

            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    print(f"  [Gemini] Rate limited on {model_name}, trying next model...")
                    break  # Skip retries, jump to next model immediately
                else:
                    print(f"  [Gemini] Error: {err[:120]}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                    else:
                        break

    print("  [Gemini] FAILED - All models failed")
    return None

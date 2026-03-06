"""Originsnap - AI-powered reverse image source finder."""

import asyncio
import os
from io import BytesIO

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from engines import saucenao, iqdb, ascii2d, tracemoe, links
from analyzer import analyze

load_dotenv()

app = FastAPI(title="Originsnap", description="AI-powered reverse image source finder")

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main page."""
    index_path = os.path.join(static_dir, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()


@app.post("/api/search")
async def search_image(file: UploadFile = File(...)):
    """Upload an image and search across all engines."""
    # Read and preprocess image
    raw_data = await file.read()
    image_data = _preprocess_image(raw_data)

    # Get config
    saucenao_key = os.getenv("SAUCENAO_API_KEY", "")
    llm_key = os.getenv("LLM_API_KEY", "")
    llm_base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # Run all search engines + external links upload concurrently
    engine_tasks = [
        saucenao.search(image_data, api_key=saucenao_key if saucenao_key else None),
        iqdb.search(image_data),
        ascii2d.search(image_data),
        tracemoe.search(image_data),
        links.generate_links(image_data),
    ]

    all_results = await asyncio.gather(*engine_tasks, return_exceptions=True)

    # Process search results (first 4), converting exceptions to error dicts
    processed_results = []
    engine_names = ["SauceNAO", "IQDB", "ASCII2D", "trace.moe"]
    for i, result in enumerate(all_results[:4]):
        if isinstance(result, Exception):
            processed_results.append({
                "engine": engine_names[i],
                "results": [],
                "error": str(result),
            })
        else:
            processed_results.append(result)

    # External links (5th result)
    external_links = all_results[4] if not isinstance(all_results[4], Exception) else {
        "engine": "external_links", "links": [], "error": str(all_results[4])
    }

    # AI analysis
    ai_result = await analyze(
        processed_results,
        api_key=llm_key,
        base_url=llm_base_url,
        model=llm_model,
    )

    return {
        "search_results": processed_results,
        "external_links": external_links,
        "analysis": ai_result.get("ai_analysis"),
        "ai_error": ai_result.get("ai_error"),
    }


def _preprocess_image(data: bytes, max_size: int = 2048) -> bytes:
    """Resize image if too large to stay within API limits."""
    try:
        img = Image.open(BytesIO(data))
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        # Convert to PNG
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return data  # Return original if processing fails

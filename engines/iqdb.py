"""IQDB reverse image search engine (HTML scraping)."""

import httpx
from bs4 import BeautifulSoup
from typing import Any

IQDB_URL = "https://iqdb.org/"


async def search(image_data: bytes) -> dict[str, Any]:
    """Search IQDB for image source.

    Returns dict with 'engine', 'results' list, and 'error' if any.
    """
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.post(
                IQDB_URL,
                files={"file": ("image.png", image_data, "image/png")},
            )
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        # Each result is in a <div> with id like "1", "2", etc. inside tables
        tables = soup.select("#pages > div table")
        for table in tables:
            # Skip "Your image" and "No relevant matches"
            header = table.select_one("th")
            if not header:
                continue
            header_text = header.get_text(strip=True)
            if "Your image" in header_text or "No relevant" in header_text:
                continue

            # Extract match info
            tds = table.select("td")
            if not tds:
                continue

            # Find link
            link_el = table.select_one("td.image a")
            source_url = ""
            thumbnail = ""
            if link_el:
                href = link_el.get("href", "")
                if href.startswith("//"):
                    source_url = "https:" + href
                elif href.startswith("/"):
                    source_url = "https://iqdb.org" + href
                else:
                    source_url = href
                img = link_el.select_one("img")
                if img:
                    src = img.get("src", "")
                    if src.startswith("//"):
                        thumbnail = "https:" + src
                    else:
                        thumbnail = src

            # Extract similarity and resolution from text
            similarity = 0.0
            resolution = ""
            rating = ""
            for td in tds:
                text = td.get_text(strip=True)
                if "% similarity" in text:
                    try:
                        similarity = float(text.split("%")[0])
                    except ValueError:
                        pass
                if "×" in text:
                    parts = text.split(",")
                    for p in parts:
                        p = p.strip()
                        if "×" in p:
                            resolution = p.split("[")[0].strip()
                        if "[" in p and "]" in p:
                            rating = p.split("[")[1].split("]")[0]

            if similarity < 50:
                continue

            # Determine source site from header
            source_site = header_text.replace("Best match", "").replace("Additional match", "").strip()

            results.append({
                "similarity": similarity,
                "source_url": source_url,
                "thumbnail": thumbnail,
                "resolution": resolution,
                "source_site": source_site,
                "rating": rating,
            })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return {"engine": "IQDB", "results": results}

    except Exception as e:
        return {"engine": "IQDB", "results": [], "error": str(e)}

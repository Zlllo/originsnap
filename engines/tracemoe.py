"""trace.moe anime scene search engine."""

import httpx
from typing import Any

TRACEMOE_API = "https://api.trace.moe/search?anilistInfo"


async def search(image_data: bytes) -> dict[str, Any]:
    """Search trace.moe for anime scene source.

    Returns dict with 'engine', 'results' list, and 'error' if any.
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                TRACEMOE_API,
                content=image_data,
                headers={"Content-Type": "image/png"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("result", [])[:8]:
            similarity = round(item.get("similarity", 0) * 100, 1)
            if similarity < 50:
                continue

            anilist = item.get("anilist", {})
            title = ""
            if isinstance(anilist, dict):
                title_obj = anilist.get("title", {})
                title = (
                    title_obj.get("native", "")
                    or title_obj.get("romaji", "")
                    or title_obj.get("english", "")
                )
                anilist_id = anilist.get("id", "")
            else:
                anilist_id = anilist

            episode = item.get("episode", "")
            from_ts = item.get("from", 0)
            to_ts = item.get("to", 0)
            mid_ts = (from_ts + to_ts) / 2

            # Format timestamp
            minutes = int(mid_ts // 60)
            seconds = int(mid_ts % 60)
            timestamp = f"{minutes:02d}:{seconds:02d}"

            result = {
                "similarity": similarity,
                "title": title,
                "episode": str(episode) if episode else "",
                "timestamp": timestamp,
                "anilist_url": f"https://anilist.co/anime/{anilist_id}" if anilist_id else "",
                "preview_video": item.get("video", ""),
                "preview_image": item.get("image", ""),
            }
            results.append(result)

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return {"engine": "trace.moe", "results": results}

    except Exception as e:
        return {"engine": "trace.moe", "results": [], "error": str(e)}

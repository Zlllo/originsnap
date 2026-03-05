"""SauceNAO reverse image search engine."""

import httpx
from typing import Any

SAUCENAO_API = "https://saucenao.com/search.php"


async def search(image_data: bytes, api_key: str | None = None) -> dict[str, Any]:
    """Search SauceNAO for image source.

    Returns dict with 'engine', 'results' list, and 'error' if any.
    Note: SauceNAO requires an API key for programmatic access.
    Get one free at https://saucenao.com/user.php
    """
    if not api_key:
        return {
            "engine": "SauceNAO",
            "results": [],
            "error": "需要 API Key（在 .env 中设置 SAUCENAO_API_KEY，可在 saucenao.com 免费注册获取）",
        }

    params: dict[str, Any] = {
        "output_type": 2,  # JSON
        "numres": 10,
        "db": 999,  # all databases
        "api_key": api_key,
    }

    try:
        async with httpx.AsyncClient(
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/131.0.0.0 Safari/537.36",
                "Accept": "application/json",
            },
        ) as client:
            resp = await client.post(
                SAUCENAO_API,
                params=params,
                files={"file": ("image.png", image_data, "image/png")},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("results", []):
            header = item.get("header", {})
            info = item.get("data", {})
            similarity = float(header.get("similarity", 0))

            if similarity < 50:
                continue

            result = {
                "similarity": similarity,
                "thumbnail": header.get("thumbnail", ""),
                "index_name": header.get("index_name", ""),
                "ext_urls": info.get("ext_urls", []),
                "title": info.get("title", ""),
                "author": _extract_author(info),
                "author_url": _extract_author_url(info),
                "source": info.get("source", ""),
            }
            results.append(result)

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return {"engine": "SauceNAO", "results": results}

    except Exception as e:
        return {"engine": "SauceNAO", "results": [], "error": str(e)}


def _extract_author(data: dict) -> str:
    """Try multiple fields to find author name."""
    for key in ("member_name", "creator", "author_name", "twitter_user_handle",
                "pawoo_user_display_name", "author"):
        val = data.get(key)
        if val:
            if isinstance(val, list):
                return ", ".join(str(v) for v in val)
            return str(val)
    return ""


def _extract_author_url(data: dict) -> str:
    """Try to find author profile URL."""
    for key in ("member_id", "pawoo_user_acct", "twitter_user_handle"):
        val = data.get(key)
        if not val:
            continue
        if key == "member_id" and data.get("pixiv_id"):
            return f"https://www.pixiv.net/users/{val}"
        if key == "twitter_user_handle":
            return f"https://x.com/{val}"
        if key == "pawoo_user_acct":
            return f"https://pawoo.net/@{val}"
    return ""

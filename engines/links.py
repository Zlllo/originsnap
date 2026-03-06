"""Generate search URLs for external reverse image search engines.

Uploads the image to a temporary image host (litterbox.catbox.moe, auto-deletes
after 1 hour) to get a public URL, then constructs search URLs for Google Lens,
Yandex, and TinEye.
"""

import httpx
from typing import Any
from urllib.parse import quote_plus

LITTERBOX_API = "https://litterbox.catbox.moe/resources/internals/api.php"


async def generate_links(image_data: bytes) -> dict[str, Any]:
    """Upload image to temp host and generate search URLs."""
    # Upload to litterbox (1-hour expiry)
    public_url = await _upload_to_litterbox(image_data)

    if not public_url:
        return {
            "engine": "external_links",
            "links": _fallback_links(),
            "error": "临时图床上传失败，请使用手动上传链接",
        }

    encoded_url = quote_plus(public_url)

    links = [
        {
            "engine": "Google Lens",
            "url": f"https://lens.google.com/uploadbyurl?url={encoded_url}",
            "icon": "🔍",
            "description": "Google Lens 图片搜索",
        },
        {
            "engine": "Yandex",
            "url": f"https://yandex.com/images/search?rpt=imageview&url={encoded_url}",
            "icon": "🔎",
            "description": "Yandex 图片搜索（俄系资源强）",
        },
        {
            "engine": "TinEye",
            "url": f"https://tineye.com/search?url={encoded_url}",
            "icon": "👁️",
            "description": "TinEye 溯源搜索（按时间排序）",
        },
    ]

    return {"engine": "external_links", "links": links, "image_url": public_url}


async def _upload_to_litterbox(image_data: bytes) -> str | None:
    """Upload image to litterbox.catbox.moe (auto-deletes after 1 hour)."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                LITTERBOX_API,
                data={"reqtype": "fileupload", "time": "1h"},
                files={"fileToUpload": ("image.png", image_data, "image/png")},
            )
            if resp.status_code == 200 and resp.text.startswith("https://"):
                return resp.text.strip()
    except Exception:
        pass
    return None


def _fallback_links() -> list[dict[str, Any]]:
    """Fallback: manual upload links when temp hosting fails."""
    return [
        {
            "engine": "Google Lens",
            "url": "https://lens.google.com/",
            "icon": "🔍",
            "description": "手动上传搜索",
        },
        {
            "engine": "Yandex",
            "url": "https://yandex.com/images/search?rpt=imageview",
            "icon": "🔎",
            "description": "手动上传搜索",
        },
        {
            "engine": "TinEye",
            "url": "https://tineye.com/",
            "icon": "👁️",
            "description": "手动上传搜索",
        },
    ]

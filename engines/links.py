"""Generate redirect URLs for external reverse image search engines."""

import base64
from typing import Any


def generate_links(image_data: bytes) -> dict[str, Any]:
    """Generate search URLs for Google Lens, Yandex, and TinEye.

    Since these services don't have free APIs, we generate URLs that
    the user can click to open the search in a new tab.

    For Google Lens and Yandex, we use base64-encoded image data URLs
    or provide instructions for the user to upload manually.
    """
    links = []

    # Google Lens - user needs to upload manually, we provide the URL
    links.append({
        "engine": "Google Lens",
        "url": "https://lens.google.com/",
        "icon": "🔍",
        "description": "Google Lens 图片搜索",
    })

    # Yandex Images
    links.append({
        "engine": "Yandex",
        "url": "https://yandex.com/images/search?rpt=imageview",
        "icon": "🔎",
        "description": "Yandex 图片搜索（俄系资源强）",
    })

    # TinEye
    links.append({
        "engine": "TinEye",
        "url": "https://tineye.com/",
        "icon": "👁️",
        "description": "TinEye 溯源搜索（按时间排序）",
    })

    return {"engine": "external_links", "links": links}

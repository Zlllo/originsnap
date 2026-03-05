"""ASCII2D reverse image search engine (HTML scraping).

Note: ASCII2D uses Cloudflare protection which may block automated requests.
When blocked, the error is handled gracefully.
"""

import httpx
from bs4 import BeautifulSoup
from typing import Any

ASCII2D_URL = "https://ascii2d.net/search/file"
ASCII2D_BOVW_PREFIX = "https://ascii2d.net/search/bovw/"  # feature search


async def search(image_data: bytes) -> dict[str, Any]:
    """Search ASCII2D for image source.

    First does color search to get the hash, then does feature (bovw) search
    which is usually more accurate for finding original sources.
    """
    try:
        async with httpx.AsyncClient(
            timeout=45,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
                          "image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
            },
        ) as client:
            # Step 1: Get CSRF token
            index_resp = await client.get("https://ascii2d.net/")
            if index_resp.status_code == 403:
                return {
                    "engine": "ASCII2D",
                    "results": [],
                    "error": "被 Cloudflare 拦截，请稍后再试或使用外部链接手动搜索",
                }

            index_soup = BeautifulSoup(index_resp.text, "html.parser")
            token_input = index_soup.select_one('input[name="authenticity_token"]')
            token = token_input["value"] if token_input else ""

            if not token:
                return {
                    "engine": "ASCII2D",
                    "results": [],
                    "error": "无法获取 CSRF token，可能被反爬拦截",
                }

            # Step 2: Upload image (color search)
            resp = await client.post(
                ASCII2D_URL,
                data={"authenticity_token": token},
                files={"file": ("image.png", image_data, "image/png")},
                headers={"Referer": "https://ascii2d.net/"},
            )

            if resp.status_code == 403:
                return {
                    "engine": "ASCII2D",
                    "results": [],
                    "error": "上传被 Cloudflare 拦截，请使用外部链接手动搜索",
                }
            resp.raise_for_status()

            # Step 3: Switch to feature search (bovw) - more accurate
            color_url = str(resp.url)
            hash_id = color_url.split("/")[-1]
            bovw_url = ASCII2D_BOVW_PREFIX + hash_id

            bovw_resp = await client.get(bovw_url)
            bovw_resp.raise_for_status()

        # Parse feature search results
        soup = BeautifulSoup(bovw_resp.text, "html.parser")
        results = []

        items = soup.select(".row.item-box")
        for item in items[1:11]:  # skip first (uploaded image), take up to 10
            info_box = item.select_one(".detail-box")
            if not info_box:
                continue

            # Extract links
            links = info_box.select("a")
            source_url = ""
            author = ""
            author_url = ""
            source_site = ""

            for link in links:
                href = link.get("href", "")
                text = link.get_text(strip=True)

                if "pixiv" in href:
                    if "/artworks/" in href or "/i/" in href:
                        source_url = href
                        source_site = "Pixiv"
                    elif "/users/" in href or "/member" in href:
                        author_url = href
                        author = text
                elif "twitter.com" in href or "x.com" in href:
                    if "/status/" in href:
                        source_url = href
                        source_site = "Twitter/X"
                    else:
                        author_url = href
                        author = text
                elif not source_url and href.startswith("http"):
                    source_url = href
                    source_site = _detect_site(href)

            # Extract title
            title_el = info_box.select_one("h6") or info_box.select_one("small")
            title = title_el.get_text(strip=True) if title_el else ""

            # Extract thumbnail
            thumbnail = ""
            img = item.select_one(".image-box img")
            if img:
                src = img.get("src", "") or img.get("data-src", "")
                if src.startswith("/"):
                    thumbnail = "https://ascii2d.net" + src
                else:
                    thumbnail = src

            if source_url or author:
                results.append({
                    "source_url": source_url,
                    "source_site": source_site,
                    "title": title,
                    "author": author,
                    "author_url": author_url,
                    "thumbnail": thumbnail,
                })

        return {"engine": "ASCII2D", "results": results}

    except Exception as e:
        return {"engine": "ASCII2D", "results": [], "error": str(e)}


def _detect_site(url: str) -> str:
    """Detect which site a URL belongs to."""
    domain_map = {
        "pixiv": "Pixiv",
        "twitter": "Twitter/X",
        "x.com": "Twitter/X",
        "deviantart": "DeviantArt",
        "artstation": "ArtStation",
        "danbooru": "Danbooru",
        "gelbooru": "Gelbooru",
        "yande.re": "Yande.re",
        "nicovideo": "Niconico",
        "fanbox": "Fanbox",
        "booth": "Booth",
    }
    for key, name in domain_map.items():
        if key in url.lower():
            return name
    return ""

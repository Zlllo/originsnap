"""AI analysis module - uses LLM to synthesize search results and determine original source."""

import json
from openai import AsyncOpenAI
from typing import Any

SYSTEM_PROMPT = """你是一个专业的图片溯源分析专家。你的任务是分析来自多个反向图片搜索引擎的结果，推断图片的最初来源和原作者。

分析规则：
1. 优先考虑高相似度的结果
2. Pixiv、Twitter/X 上的原始发布通常是插画的第一来源
3. Booru 站（Danbooru、Gelbooru 等）通常是转载，不是原始来源，但它们的标签信息有参考价值
4. 如果多个引擎指向同一个作者/来源，置信度更高
5. 较早的发布日期通常意味着更接近原始来源
6. trace.moe 的结果说明这是动漫截图，给出番剧信息即可

请用以下 JSON 格式回复（不要包含 markdown 代码块标记）：
{
  "conclusion": "对图片来源的简要结论（中文，1-2句话）",
  "original_source": {
    "url": "最可能的原始来源 URL",
    "platform": "平台名称",
    "title": "作品标题（如有）"
  },
  "author": {
    "name": "原作者名",
    "profile_url": "作者主页 URL"
  },
  "confidence": "high/medium/low",
  "reasoning": "简要推理过程（中文，2-3句话）",
  "is_anime_screenshot": false,
  "anime_info": null
}

如果是动漫截图，anime_info 格式：
{
  "title": "番剧名",
  "episode": "集数",
  "timestamp": "时间戳"
}"""


async def analyze(
    search_results: list[dict[str, Any]],
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
) -> dict[str, Any]:
    """Use LLM to analyze aggregated search results and determine original source."""
    if not api_key:
        return _fallback_analyze(search_results)

    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        # Format results for LLM
        formatted = _format_results_for_llm(search_results)

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"以下是各搜索引擎的结果，请分析：\n\n{formatted}"},
            ],
            temperature=0.3,
            max_tokens=1000,
        )

        content = response.choices[0].message.content.strip()
        # Clean markdown code block if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        return {"ai_analysis": json.loads(content), "raw_response": content}

    except Exception as e:
        # Fall back to simple heuristic analysis
        result = _fallback_analyze(search_results)
        result["ai_error"] = str(e)
        return result


def _format_results_for_llm(search_results: list[dict[str, Any]]) -> str:
    """Format search results into readable text for the LLM."""
    parts = []
    for engine_result in search_results:
        engine = engine_result.get("engine", "Unknown")
        results = engine_result.get("results", [])
        error = engine_result.get("error")

        if error:
            parts.append(f"## {engine}\n搜索出错: {error}\n")
            continue
        if not results:
            parts.append(f"## {engine}\n无结果\n")
            continue

        lines = [f"## {engine}"]
        for i, r in enumerate(results[:5], 1):
            line = f"{i}."
            if "similarity" in r:
                line += f" 相似度: {r['similarity']}%"
            if r.get("title"):
                line += f" | 标题: {r['title']}"
            if r.get("author"):
                line += f" | 作者: {r['author']}"
            if r.get("author_url"):
                line += f" | 作者主页: {r['author_url']}"
            if r.get("source_url"):
                line += f" | 来源: {r['source_url']}"
            if r.get("ext_urls"):
                line += f" | 链接: {', '.join(r['ext_urls'][:3])}"
            if r.get("source_site"):
                line += f" | 站点: {r['source_site']}"
            if r.get("episode"):
                line += f" | 集数: {r['episode']}"
            if r.get("timestamp"):
                line += f" | 时间: {r['timestamp']}"
            if r.get("anilist_url"):
                line += f" | AniList: {r['anilist_url']}"
            lines.append(line)
        parts.append("\n".join(lines) + "\n")

    return "\n".join(parts)


def _fallback_analyze(search_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Simple heuristic analysis when LLM is not available."""
    best_source = None
    best_author = None
    best_similarity = 0
    is_anime = False
    anime_info = None

    for engine_result in search_results:
        engine = engine_result.get("engine", "")
        for r in engine_result.get("results", []):
            sim = r.get("similarity", 0)

            # Check trace.moe for anime
            if engine == "trace.moe" and sim > 85:
                is_anime = True
                anime_info = {
                    "title": r.get("title", ""),
                    "episode": r.get("episode", ""),
                    "timestamp": r.get("timestamp", ""),
                }

            # Track best source
            if sim > best_similarity:
                url = r.get("ext_urls", [None])[0] if r.get("ext_urls") else r.get("source_url", "")
                if url:
                    best_similarity = sim
                    best_source = {
                        "url": url,
                        "platform": r.get("source_site", r.get("index_name", "")),
                        "title": r.get("title", ""),
                    }
                    if r.get("author"):
                        best_author = {
                            "name": r["author"],
                            "profile_url": r.get("author_url", ""),
                        }

    confidence = "high" if best_similarity > 90 else "medium" if best_similarity > 70 else "low"

    return {
        "ai_analysis": {
            "conclusion": f"基于搜索结果的自动分析（未使用 AI，请配置 LLM API 以获得更准确的分析）",
            "original_source": best_source or {"url": "", "platform": "", "title": ""},
            "author": best_author or {"name": "", "profile_url": ""},
            "confidence": confidence,
            "reasoning": f"最高相似度 {best_similarity}%，来自自动匹配。",
            "is_anime_screenshot": is_anime,
            "anime_info": anime_info,
        }
    }

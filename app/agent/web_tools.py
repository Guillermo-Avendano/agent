"""Web search tool using Browserless Chromium.

Scrapes search results and web pages to answer questions
that are outside the database domain.
"""

import re
from urllib.parse import quote_plus

import httpx
import structlog
from langchain_core.tools import tool

from app.config import settings

logger = structlog.get_logger(__name__)

# DuckDuckGo HTML search (no API key needed)
_SEARCH_URL = "https://html.duckduckgo.com/html/?q={query}"


async def _fetch_via_browserless(url: str) -> str:
    """Use Browserless Chromium to render a page and extract text content."""
    browserless_url = f"{settings.browserless_url}/content"
    payload = {
        "url": url,
        "waitForSelector": {"selector": "body", "timeout": 10000},
        "gotoOptions": {"waitUntil": "domcontentloaded", "timeout": 15000},
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            browserless_url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        html = resp.text

    # Extract readable text from HTML (simple approach)
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Limit to ~4000 chars to keep context manageable
    return text[:4000]


async def _search_duckduckgo(query: str, max_results: int = 3) -> list[dict]:
    """Search DuckDuckGo via Browserless and extract result links + snippets."""
    url = _SEARCH_URL.format(query=quote_plus(query))
    try:
        html = await _fetch_via_browserless(url)
    except Exception as e:
        logger.warning("web_search.duckduckgo_failed", error=str(e))
        return []

    # Parse result snippets (simple regex on DDG HTML results)
    results = []

    # DDG HTML results have class="result__a" for links and "result__snippet" for text
    links = re.findall(r'href="(https?://[^"]+)"', html)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)<', html, re.DOTALL)

    # Filter out DDG internal links
    external_links = [
        link for link in links
        if "duckduckgo.com" not in link and "duck.co" not in link
    ]

    for i, link in enumerate(external_links[:max_results]):
        snippet = snippets[i].strip() if i < len(snippets) else ""
        snippet = re.sub(r"<[^>]+>", "", snippet)  # clean HTML tags from snippet
        results.append({"url": link, "snippet": snippet})

    return results


@tool
async def web_search(query: str) -> str:
    """Search the internet for information not available in the database.

    Use this when the user's question is about general knowledge, current events,
    or anything outside the PostgreSQL database scope.

    Args:
        query: The search query string.
    """
    logger.info("web_search.start", query=query[:100])
    try:
        results = await _search_duckduckgo(query)
        if not results:
            return "Web search returned no results. Try rephrasing the query."

        # Fetch content from the top result for a detailed answer
        top_url = results[0]["url"]
        page_content = ""
        try:
            page_content = await _fetch_via_browserless(top_url)
        except Exception as e:
            logger.warning("web_search.page_fetch_failed", url=top_url, error=str(e))

        output_parts = ["## Web Search Results\n"]
        for i, r in enumerate(results, 1):
            output_parts.append(f"**{i}. {r['url']}**\n{r['snippet']}\n")

        if page_content:
            output_parts.append(f"\n## Top Result Content\n{page_content[:3000]}")

        return "\n".join(output_parts)

    except Exception as e:
        logger.error("web_search.error", error=str(e))
        return f"Web search error: {e}"


@tool
async def fetch_webpage(url: str) -> str:
    """Fetch and extract text content from a specific webpage URL.

    Use this when you need to read a specific web page the user mentioned
    or to get more details from a search result.

    Args:
        url: The full URL of the webpage to fetch.
    """
    logger.info("fetch_webpage.start", url=url[:100])
    try:
        content = await _fetch_via_browserless(url)
        if not content:
            return "Could not extract content from this page."
        return content
    except Exception as e:
        logger.error("fetch_webpage.error", error=str(e))
        return f"Failed to fetch page: {e}"


WEB_TOOLS = [web_search, fetch_webpage]

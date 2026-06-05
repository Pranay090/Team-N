"""Shared Tavily search client and helper."""
import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


def tavily_search(
    query: str,
    max_results: int = 7,
    include_domains: list[str] | None = None,
    days: int | None = None,
) -> list[dict]:
    """Returns raw Tavily result dicts: {url, title, content, score}."""
    kwargs: dict = {
        "query": query,
        "max_results": max_results,
        "search_depth": "advanced",
        "include_raw_content": False,
    }
    if include_domains:
        kwargs["include_domains"] = include_domains
    if days:
        kwargs["days"] = days

    response = _client.search(**kwargs)
    return response.get("results", [])

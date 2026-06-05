"""Node 2B — Product scraper. Targets review and commerce sites via Tavily."""
from src.agent.state import AgentState, RawResult
from src.agent.search import tavily_search

_PRODUCT_DOMAINS = [
    "rtings.com",
    "wirecutter.com",
    "tomsguide.com",
    "techradar.com",
    "reddit.com",
    "cnet.com",
    "theverge.com",
]


def scrape_products(state: AgentState) -> dict:
    query = state.get("resolved_query") or state["query"]
    search_query = f"{query} review best recommendations 2024 2025"

    hits = tavily_search(
        query=search_query,
        max_results=8,
        include_domains=_PRODUCT_DOMAINS,
    )

    raw: list[RawResult] = [
        {
            "url": h["url"],
            "title": h.get("title", ""),
            "snippet": h.get("content", ""),
            "source": "product",
            "raw_html": None,
        }
        for h in hits
    ]
    print(f"[ProductScraper] {len(raw)} results for: {query}")
    return {"raw_results": raw}

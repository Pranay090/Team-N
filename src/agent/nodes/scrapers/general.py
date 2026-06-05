"""Node 2C — General scraper. Open web search via Tavily."""
from src.agent.state import AgentState, RawResult
from src.agent.search import tavily_search


def scrape_general(state: AgentState) -> dict:
    query = state["query"]

    hits = tavily_search(query=query, max_results=8)

    raw: list[RawResult] = [
        {
            "url": h["url"],
            "title": h.get("title", ""),
            "snippet": h.get("content", ""),
            "source": "general",
            "raw_html": None,
        }
        for h in hits
    ]
    print(f"[GeneralScraper] {len(raw)} results")
    return {"raw_results": raw}

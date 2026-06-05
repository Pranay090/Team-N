"""Node 2A — Job scraper. Targets LinkedIn / Indeed / Glassdoor via Tavily."""
from src.agent.state import AgentState, RawResult
from src.agent.search import tavily_search

_JOB_DOMAINS = [
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "wellfound.com",
    "remoteok.com",
    "weworkremotely.com",
]


def scrape_jobs(state: AgentState) -> dict:
    query = state.get("resolved_query") or state["query"]
    search_query = f"{query} job listing site:linkedin.com OR site:indeed.com OR site:glassdoor.com"

    hits = tavily_search(
        query=search_query,
        max_results=10,
        include_domains=_JOB_DOMAINS,
        days=7,  # only listings from the past week
    )

    raw: list[RawResult] = [
        {
            "url": h["url"],
            "title": h.get("title", ""),
            "snippet": h.get("content", ""),
            "source": "job_board",
            "raw_html": None,
        }
        for h in hits
    ]
    print(f"[JobScraper] {len(raw)} results for: {query}")
    return {"raw_results": raw}

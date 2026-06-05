"""Node 4 — Ranker. Scores valid results by domain trust + query relevance."""
import re
from urllib.parse import urlparse

from src.agent.state import AgentState, RankedResult

_TRUST_SCORES: dict[str, float] = {
    # Job boards
    "linkedin.com": 1.0, "indeed.com": 1.0, "glassdoor.com": 0.95,
    "wellfound.com": 0.90, "remoteok.com": 0.85, "weworkremotely.com": 0.85,
    # Product / review
    "wirecutter.com": 1.0, "rtings.com": 1.0, "tomsguide.com": 0.90,
    "techradar.com": 0.88, "cnet.com": 0.88, "theverge.com": 0.88,
    "tomshardware.com": 0.90, "reddit.com": 0.75,
    # General
    "wikipedia.org": 1.0, "github.com": 0.95, "stackoverflow.com": 0.95,
    "arxiv.org": 0.95, "medium.com": 0.70, "deeplearning.ai": 0.90,
}

_TOP_K = 8  # keep this many after ranking


def _root_domain(url: str) -> str:
    host = urlparse(url).hostname or ""
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def _trust(url: str) -> float:
    domain = _root_domain(url)
    return _TRUST_SCORES.get(domain, 0.5)


def _relevance(query: str, title: str, snippet: str) -> float:
    """Keyword overlap between query tokens and title+snippet."""
    tokens = set(re.findall(r"\w+", query.lower()))
    if not tokens:
        return 0.5
    text = f"{title} {snippet}".lower()
    hits = sum(1 for t in tokens if t in text)
    return min(hits / len(tokens), 1.0)


def rank_results(state: AgentState) -> dict:
    valid = state["valid_results"]
    query = state["query"]

    ranked: list[RankedResult] = []
    for r in valid:
        trust = _trust(r["url"])
        relevance = _relevance(query, r["title"], r["snippet"])
        # Weights: trust 40%, relevance 60%
        score = round(0.4 * trust + 0.6 * relevance, 4)
        ranked.append({**r, "score": score})  # type: ignore[misc]

    ranked.sort(key=lambda x: x["score"], reverse=True)
    top = ranked[:_TOP_K]

    print(f"[Ranker] Top {len(top)} results (scores: {[r['score'] for r in top]})")
    return {"ranked_results": top}

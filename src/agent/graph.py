"""LangGraph graph definition — wires all nodes into the pipeline."""
from langgraph.graph import StateGraph, END

from src.agent.state import AgentState
from src.agent.nodes.query_resolver import resolve_query
from src.agent.nodes.clarification import check_clarification
from src.agent.nodes.intent import classify_intent
from src.agent.nodes.scrapers.job import scrape_jobs
from src.agent.nodes.scrapers.product import scrape_products
from src.agent.nodes.scrapers.general import scrape_general
from src.agent.nodes.validator import validate_results
from src.agent.nodes.ranker import rank_results
from src.agent.nodes.extractor import extract_and_summarize
from src.agent.nodes.next_actions import build_next_actions


def _route_clarification(state: AgentState) -> str:
    if state.get("needs_clarification"):
        return END
    return "scrape_router"


def _route_by_intent(state: AgentState) -> str:
    intent = state.get("intent", "general")
    if intent == "job":
        return "scrape_jobs"
    if intent == "product":
        return "scrape_products"
    return "scrape_general"


def _scrape_router(state: AgentState) -> dict:
    """Passthrough node used as a hub for the intent conditional edge."""
    return {}


def build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    # Nodes
    g.add_node("resolve_query",        resolve_query)
    g.add_node("classify_intent",      classify_intent)
    g.add_node("check_clarification",  check_clarification)
    g.add_node("scrape_router",        _scrape_router)
    g.add_node("scrape_jobs",          scrape_jobs)
    g.add_node("scrape_products",      scrape_products)
    g.add_node("scrape_general",       scrape_general)
    g.add_node("validate_results",     validate_results)
    g.add_node("rank_results",         rank_results)
    g.add_node("extract_and_summarize",extract_and_summarize)
    g.add_node("build_next_actions",   build_next_actions)

    # Entry: resolve → intent → clarification gate
    g.set_entry_point("resolve_query")
    g.add_edge("resolve_query",       "classify_intent")
    g.add_edge("classify_intent",     "check_clarification")

    # Clarification gate: stop early or continue to scraping
    g.add_conditional_edges(
        "check_clarification",
        _route_clarification,
        {END: END, "scrape_router": "scrape_router"},
    )

    # Intent routing to the right scraper
    g.add_conditional_edges(
        "scrape_router",
        _route_by_intent,
        {
            "scrape_jobs":     "scrape_jobs",
            "scrape_products": "scrape_products",
            "scrape_general":  "scrape_general",
        },
    )

    for scraper in ("scrape_jobs", "scrape_products", "scrape_general"):
        g.add_edge(scraper, "validate_results")

    g.add_edge("validate_results",      "rank_results")
    g.add_edge("rank_results",          "extract_and_summarize")
    g.add_edge("extract_and_summarize", "build_next_actions")
    g.add_edge("build_next_actions",    END)

    return g.compile()


graph = build_graph()

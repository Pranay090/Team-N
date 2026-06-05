from typing import Annotated, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class RawResult(TypedDict):
    url: str
    title: str
    snippet: str
    source: str  # "job_board" | "product" | "general"
    raw_html: str | None


class RankedResult(TypedDict):
    url: str
    title: str
    snippet: str
    source: str
    score: float  # 0.0 – 1.0


class SummaryCard(TypedDict):
    title: str
    url: str
    summary: str
    metadata: dict[str, str]  # company, location, salary, price, rating


class NextAction(TypedDict):
    label: str   # "Apply Now", "View Product", "Open Link"
    url: str
    description: str


class AgentState(TypedDict):
    # Conversation
    messages: Annotated[list, add_messages]

    # Derived from the latest user message
    query: str
    intent: str  # "job" | "product" | "general"

    # Pipeline stages
    raw_results: list[RawResult]
    valid_results: list[RawResult]
    ranked_results: list[RankedResult]
    summary_cards: list[SummaryCard]
    next_actions: list[NextAction]

    # Final answer rendered in the UI
    answer: str

"""Node 0A — Query Resolver.

Rewrites a follow-up query into a complete standalone question by
injecting relevant entities (names, places, products) from the
conversation history. Fresh queries are returned unchanged.
"""
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate

from src.agent.llm import llm
from src.agent.state import AgentState


class _Resolution(BaseModel):
    resolved_query: str
    is_followup: bool


_SYSTEM = """You are a query resolver for a web-search assistant.

Given the recent conversation history and the latest user message:
- If the message is a follow-up that references previous results using
  words like "these", "them", "those", "their", "above", "that place", etc.,
  rewrite it as a COMPLETE, self-contained search query by substituting
  the actual entity names from the conversation history.
- If it is a fresh, independent question, return it exactly as-is.

Examples
--------
History:
  user: best biryanis in Hyderabad
  assistant: Top picks are Paradise Biryani, Bawarchi, Shah Ghouse...

New message: "what are the prices in these restaurants"
resolved_query: "prices at Paradise Biryani, Bawarchi, Shah Ghouse in Hyderabad"
is_followup: true

---
History: (empty)
New message: "Find me remote Python developer jobs"
resolved_query: "Find me remote Python developer jobs"
is_followup: false
"""

_HUMAN = """Conversation history:
{history}

Latest user message: {query}"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", _HUMAN),
])

_chain = _prompt | llm.with_structured_output(_Resolution, method="function_calling")


def _format_history(history: list[dict]) -> str:
    if not history:
        return "(none)"
    lines = []
    for turn in history[-6:]:  # last 3 back-and-forth turns
        role = turn.get("role", "user")
        content = str(turn.get("content", ""))[:300]  # truncate long answers
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def resolve_query(state: AgentState) -> dict:
    query = state["query"]
    history = state.get("conversation_history", [])

    if not history:
        # No history — nothing to resolve
        print(f"[QueryResolver] Fresh query: {query}")
        return {"resolved_query": query}

    result: _Resolution = _chain.invoke({
        "history": _format_history(history),
        "query": query,
    })

    if result.is_followup:
        print(f"[QueryResolver] Follow-up rewritten: '{query}' → '{result.resolved_query}'")
    else:
        print(f"[QueryResolver] Fresh query (no rewrite needed)")

    return {"resolved_query": result.resolved_query}

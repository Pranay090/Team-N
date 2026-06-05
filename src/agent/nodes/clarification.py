"""Node 0B — Clarification Gate.

Decides whether the query needs more context before searching.
Asks at most 2 focused questions. If the query is already specific
enough, passes straight through.
"""
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate

from src.agent.llm import llm
from src.agent.state import AgentState


class _ClarificationDecision(BaseModel):
    needs_clarification: bool
    questions: list[str]   # max 2 items; empty when needs_clarification=false


_SYSTEM = """You are a clarification assistant for a web-search agent.

Decide if the user's query needs more detail to return truly useful results.

Rules by intent
---------------
job      → Ask about: role/skills (if missing), city or remote preference (if missing),
           experience level or salary (if missing). Skip if all three are clear.
product  → Ask about: budget (if missing), primary use-case (if missing).
           Skip if both are clear or the query is already very specific.
general  → Almost never need clarification. Only ask if the query is genuinely
           ambiguous (e.g. bare single word "Python").
food/restaurant (general intent) → Ask about: city/area (if missing), budget per person (if missing).

Important
---------
- Return needs_clarification=false if the query already has enough detail.
- Maximum 2 questions. Make them short and conversational.
- If the user says "just show me something" or "give me general info", return needs_clarification=false.
- A follow-up query (e.g. "what are the prices there?") never needs clarification."""

_HUMAN = """Intent: {intent}
Query: {query}"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", _HUMAN),
])

_chain = _prompt | llm.with_structured_output(
    _ClarificationDecision, method="function_calling"
)


def check_clarification(state: AgentState) -> dict:
    query   = state["resolved_query"]
    intent  = state["intent"]
    history = state.get("conversation_history", [])

    # Never re-clarify a follow-up question
    if history and len(history) >= 2:
        last_role = history[-1].get("role") if history else None
        if last_role == "assistant":
            print("[Clarification] Follow-up detected — skipping clarification")
            return {"needs_clarification": False, "clarification_questions": []}

    decision: _ClarificationDecision = _chain.invoke({
        "intent": intent,
        "query":  query,
    })

    if decision.needs_clarification:
        print(f"[Clarification] Needs info — questions: {decision.questions}")
    else:
        print("[Clarification] Query is specific enough — proceeding")

    return {
        "needs_clarification": decision.needs_clarification,
        "clarification_questions": decision.questions[:2],
    }

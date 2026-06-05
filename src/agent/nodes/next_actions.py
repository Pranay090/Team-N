"""Node 6 — Next Actions. Builds CTA deeplinks and follow-up suggestions."""
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate

from src.agent.llm import llm
from src.agent.state import AgentState, NextAction

# ── CTA labels by intent ──────────────────────────────────────────────────────

_CTA = {
    "job":     {"label": "Apply Now",     "prefix": "Apply for"},
    "product": {"label": "View Product",  "prefix": "View"},
    "general": {"label": "Read More",     "prefix": "Read"},
}

# ── Follow-up suggestion model ────────────────────────────────────────────────

class _FollowUps(BaseModel):
    questions: list[str]  # exactly 3 follow-up questions


_FOLLOWUP_SYSTEM = """You are a helpful assistant. Given a user query and the answer just provided,
suggest exactly 3 concise follow-up questions the user might naturally want to ask next.
Each question should be on one line, no numbering, no bullet points."""

_followup_prompt = ChatPromptTemplate.from_messages([
    ("system", _FOLLOWUP_SYSTEM),
    ("human", "Query: {query}\n\nAnswer summary: {answer}"),
])

_followup_chain = _followup_prompt | llm.with_structured_output(
    _FollowUps, method="function_calling"
)

# ── Node ──────────────────────────────────────────────────────────────────────

def build_next_actions(state: AgentState) -> dict:
    intent  = state.get("intent", "general")
    cards   = state["summary_cards"]
    query   = state["query"]
    answer  = state["answer"]

    cta = _CTA.get(intent, _CTA["general"])

    # One CTA button per card
    actions: list[NextAction] = [
        {
            "label":       f"{cta['label']} →",
            "url":         card["url"],
            "description": f"{cta['prefix']}: {card['title']}",
        }
        for card in cards
        if card.get("url")
    ]

    # LLM follow-up suggestions
    followups: list[str] = []
    try:
        result: _FollowUps = _followup_chain.invoke({
            "query":  query,
            "answer": answer[:600],  # keep prompt short
        })
        followups = result.questions[:3]
    except Exception as e:
        print(f"[NextActions] Follow-up generation failed: {e}")

    # Append follow-ups to the answer as a markdown section
    updated_answer = answer
    if followups:
        suggestions = "\n".join(f"- {q}" for q in followups)
        updated_answer += f"\n\n---\n**You might also want to ask:**\n{suggestions}"

    print(f"[NextActions] {len(actions)} CTAs | {len(followups)} follow-ups")
    return {"next_actions": actions, "answer": updated_answer}

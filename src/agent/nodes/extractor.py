"""Node 5 — Extractor & Summarizer. Generates clean markdown cards via LLM."""
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from src.agent.llm import llm
from src.agent.state import AgentState, SummaryCard


class _CardMeta(BaseModel):
    company: str = ""
    location: str = ""
    salary: str = ""
    price: str = ""
    rating: str = ""


class _Card(BaseModel):
    title: str
    url: str
    summary: str
    metadata: _CardMeta


class _ExtractorOutput(BaseModel):
    cards: list[_Card]
    answer: str  # full markdown answer to render in the UI


_SYSTEM = """You are an expert research assistant. Given a user query and a list of web results,
produce two things:
1. A structured list of result cards (one per source).
2. A single, well-formatted markdown answer that directly addresses the query.

Rules:
- Be factual and concise. Only use information present in the snippets.
- For job results: include title, company (if found), location, salary (if mentioned).
- For product results: include product name, price range (if mentioned), key pros.
- For general results: include the key insight or fact from each source.
- In the final answer, cite sources inline as [Title](url).
- Keep the answer under 400 words."""

_HUMAN = """Query: {query}

Results:
{results_block}"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", _HUMAN),
])

_chain = _prompt | llm.with_structured_output(_ExtractorOutput, method="function_calling")


def _format_results(ranked_results: list) -> str:
    lines = []
    for i, r in enumerate(ranked_results, 1):
        lines.append(f"[{i}] {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}\n")
    return "\n".join(lines)


def extract_and_summarize(state: AgentState) -> dict:
    ranked = state["ranked_results"]

    if not ranked:
        return {
            "summary_cards": [],
            "answer": "I couldn't find any reliable results for your query. Please try rephrasing.",
        }

    results_block = _format_results(ranked)
    output: _ExtractorOutput = _chain.invoke({
        "query": state["query"],
        "results_block": results_block,
    })

    cards: list[SummaryCard] = [
        {
            "title": c.title,
            "url": c.url,
            "summary": c.summary,
            "metadata": c.metadata.model_dump(exclude_none=True),
        }
        for c in output.cards
    ]

    print(f"[Extractor] Generated {len(cards)} cards")
    return {"summary_cards": cards, "answer": output.answer}

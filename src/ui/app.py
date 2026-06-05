"""Streamlit Chat UI for Aiden AI."""
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.agent.graph import graph  # noqa: E402

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="Aiden AI", page_icon="🔍", layout="centered")

st.markdown("""
<style>
.intent-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 8px;
}
.badge-job     { background:#dbeafe; color:#1d4ed8; }
.badge-product { background:#dcfce7; color:#15803d; }
.badge-general { background:#fef3c7; color:#b45309; }
.followup-hint { font-size: 0.8rem; color: #6b7280; margin-bottom: 4px; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────

if "messages"       not in st.session_state:
    st.session_state.messages        = []
if "pending_query"  not in st.session_state:
    st.session_state.pending_query   = None
if "clarification"  not in st.session_state:
    # Tracks an in-progress clarification flow
    # { active, original_query, questions }
    st.session_state.clarification   = {"active": False, "original_query": "", "questions": []}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _conversation_history() -> list[dict]:
    """Last 6 turns (user + assistant) for the query resolver."""
    history = []
    for msg in st.session_state.messages[-6:]:
        if msg["role"] == "user":
            history.append({"role": "user", "content": msg["content"]})
        else:
            history.append({"role": "assistant", "content": msg.get("content", "")[:400]})
    return history


def _split_answer(answer: str) -> tuple[str, list[str]]:
    sep = "\n\n---\n**You might also want to ask:**\n"
    if sep in answer:
        main, block = answer.split(sep, 1)
        followups = [l.lstrip("- ").strip() for l in block.strip().splitlines() if l.strip()]
        return main, followups
    return answer, []


def _invoke_graph(query: str) -> dict:
    return graph.invoke({
        "messages":             [{"role": "user", "content": query}],
        "query":                query,
        "resolved_query":       "",
        "intent":               "",
        "needs_clarification":  False,
        "clarification_questions": [],
        "conversation_history": _conversation_history(),
        "raw_results":          [],
        "valid_results":        [],
        "ranked_results":       [],
        "summary_cards":        [],
        "next_actions":         [],
        "answer":               "",
    })


def _run_query(query: str) -> None:
    """Run the graph for a query; handle clarification or answer."""
    st.session_state.messages.append({"role": "user", "content": query})

    with st.spinner("Thinking…"):
        result = _invoke_graph(query)

    # ── Clarification needed ──────────────────────────────────────────────────
    if result.get("needs_clarification"):
        questions = result.get("clarification_questions", [])
        st.session_state.clarification = {
            "active":         True,
            "original_query": query,
            "questions":      questions,
        }
        # Show as assistant message so the chat history looks natural
        clarification_text = (
            "Before I search, let me ask a couple of quick questions to give you better results:\n\n"
            + "\n".join(f"- {q}" for q in questions)
        )
        st.session_state.messages.append({
            "role":    "assistant",
            "content": clarification_text,
            "mode":    "clarification",
            "questions": questions,
        })
        return

    # ── Normal answer ─────────────────────────────────────────────────────────
    raw_answer = result.get("answer", "No answer generated.")
    main_answer, followups = _split_answer(raw_answer)

    st.session_state.messages.append({
        "role":         "assistant",
        "content":      main_answer,
        "mode":         "answer",
        "intent":       result.get("intent", "general"),
        "next_actions": result.get("next_actions", []),
        "followups":    followups,
        "cards":        result.get("summary_cards", []),
    })

    # Clear any lingering clarification state
    st.session_state.clarification = {"active": False, "original_query": "", "questions": []}


def _render_sources(cards: list) -> None:
    with st.expander(f"📄 {len(cards)} sources", expanded=False):
        for card in cards:
            meta   = card.get("metadata", {})
            fields = ["company", "location", "salary", "price", "rating"]
            detail = "  ·  ".join(meta[f] for f in fields if meta.get(f))
            st.markdown(f"**[{card['title']}]({card['url']})**")
            if detail:
                st.caption(detail)
            st.caption(card.get("summary", "")[:200])
            st.divider()


def _render_cta_buttons(actions: list) -> None:
    cols = st.columns(min(len(actions), 4))
    for i, action in enumerate(actions[:4]):
        cols[i].link_button(action["label"], action["url"], use_container_width=True)


def _render_followup_chips(followups: list, msg_idx: int) -> None:
    st.markdown('<p class="followup-hint">Suggested follow-ups:</p>', unsafe_allow_html=True)
    cols = st.columns(len(followups))
    for i, (col, q) in enumerate(zip(cols, followups)):
        if col.button(q, key=f"fu_{msg_idx}_{i}", use_container_width=True):
            st.session_state.pending_query = q


def _render_assistant(msg: dict, msg_idx: int) -> None:
    if msg.get("mode") == "clarification":
        st.markdown(msg["content"])
        return

    intent = msg.get("intent", "general")
    st.markdown(
        f'<span class="intent-badge badge-{intent}">{intent}</span>',
        unsafe_allow_html=True,
    )
    st.markdown(msg["content"])

    if msg.get("cards"):
        _render_sources(msg["cards"])
    if msg.get("next_actions"):
        _render_cta_buttons(msg["next_actions"])
    if msg.get("followups"):
        _render_followup_chips(msg["followups"], msg_idx)

# ── Render history ────────────────────────────────────────────────────────────

st.title("🔍 Aiden AI")
st.caption("Intelligent web crawler · jobs · products · general Q&A")

for idx, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant"):
            _render_assistant(msg, idx)

# ── Clarification form (shown when agent asks questions) ─────────────────────

clarif = st.session_state.clarification
if clarif["active"]:
    with st.form("clarification_form", clear_on_submit=True):
        st.markdown("**Your answers:**")
        answers = []
        for q in clarif["questions"]:
            answers.append(st.text_input(q, key=f"cq_{q[:20]}"))
        submitted = st.form_submit_button("Search Now 🔍", use_container_width=True)

    if submitted:
        filled = [(q, a) for q, a in zip(clarif["questions"], answers) if a.strip()]
        if filled:
            context = ". ".join(f"{q}: {a}" for q, a in filled)
            combined = f"{clarif['original_query']}. {context}"
        else:
            combined = clarif["original_query"]
        st.session_state.clarification = {"active": False, "original_query": "", "questions": []}
        st.session_state.pending_query = combined
        st.rerun()

# ── Handle follow-up chip or pending query ────────────────────────────────────

elif st.session_state.pending_query:
    query = st.session_state.pending_query
    st.session_state.pending_query = None
    _run_query(query)
    st.rerun()

# ── Chat input (hidden while clarification form is active) ───────────────────

if not clarif["active"]:
    if prompt := st.chat_input("Ask me anything — jobs, products, or general questions…"):
        _run_query(prompt)
        st.rerun()

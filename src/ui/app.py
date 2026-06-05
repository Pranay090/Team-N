"""Streamlit Chat UI for Aiden AI."""
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.agent.graph import graph  # noqa: E402

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Aiden AI",
    page_icon="🔍",
    layout="centered",
)

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

.followup-hint {
    font-size: 0.8rem;
    color: #6b7280;
    margin-bottom: 4px;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []     # list of dicts, see _make_msg()
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

# ── Helpers ───────────────────────────────────────────────────────────────────

def _split_answer(answer: str) -> tuple[str, list[str]]:
    """Separate main answer text from appended follow-up suggestions."""
    sep = "\n\n---\n**You might also want to ask:**\n"
    if sep in answer:
        main, block = answer.split(sep, 1)
        followups = [
            line.lstrip("- ").strip()
            for line in block.strip().splitlines()
            if line.strip()
        ]
        return main, followups
    return answer, []


def _run_query(query: str) -> None:
    """Invoke the graph and append both user and assistant messages."""
    st.session_state.messages.append({"role": "user", "content": query})

    with st.spinner("Searching the web…"):
        result = graph.invoke({
            "messages": [{"role": "user", "content": query}],
            "query": query,
            "intent": "",
            "raw_results": [],
            "valid_results": [],
            "ranked_results": [],
            "summary_cards": [],
            "next_actions": [],
            "answer": "",
        })

    raw_answer = result.get("answer", "No answer generated.")
    main_answer, followups = _split_answer(raw_answer)

    st.session_state.messages.append({
        "role":         "assistant",
        "content":      main_answer,
        "intent":       result.get("intent", "general"),
        "next_actions": result.get("next_actions", []),
        "followups":    followups,
        "cards":        result.get("summary_cards", []),
    })


def _render_assistant(msg: dict, msg_idx: int) -> None:
    intent = msg.get("intent", "general")
    badge_class = f"badge-{intent}"
    st.markdown(
        f'<span class="intent-badge {badge_class}">{intent}</span>',
        unsafe_allow_html=True,
    )

    # Main answer
    st.markdown(msg["content"])

    # Source cards in expander
    cards = msg.get("cards", [])
    if cards:
        with st.expander(f"📄 {len(cards)} sources", expanded=False):
            for card in cards:
                meta = card.get("metadata", {})
                detail = "  ·  ".join(v for v in [
                    meta.get("company"), meta.get("location"),
                    meta.get("salary"), meta.get("price"), meta.get("rating"),
                ] if v)
                st.markdown(f"**[{card['title']}]({card['url']})**")
                if detail:
                    st.caption(detail)
                st.caption(card.get("summary", "")[:200])
                st.divider()

    # CTA buttons
    actions = msg.get("next_actions", [])
    if actions:
        cols = st.columns(min(len(actions), 4))
        for i, action in enumerate(actions[:4]):
            cols[i].link_button(action["label"], action["url"], use_container_width=True)

    # Follow-up suggestion chips
    followups = msg.get("followups", [])
    if followups:
        st.markdown('<p class="followup-hint">Suggested follow-ups:</p>', unsafe_allow_html=True)
        cols = st.columns(len(followups))
        for i, (col, q) in enumerate(zip(cols, followups)):
            if col.button(q, key=f"fu_{msg_idx}_{i}", use_container_width=True):
                st.session_state.pending_query = q


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

# ── Handle follow-up chip clicks ──────────────────────────────────────────────

if st.session_state.pending_query:
    query = st.session_state.pending_query
    st.session_state.pending_query = None
    _run_query(query)
    st.rerun()

# ── Chat input ────────────────────────────────────────────────────────────────

if prompt := st.chat_input("Ask me anything — jobs, products, or general questions…"):
    _run_query(prompt)
    st.rerun()

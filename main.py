"""
main.py
-------
Streamlit UI for Tina — Travel Planning Chatbot.
Clean chat window. Memory is maintained per session via LangGraph MemorySaver.
"""

import streamlit as st
import uuid
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Validate required env vars at startup — fail fast, never expose key values
_REQUIRED_ENV_VARS = ["OPENAI_API_KEY"]
_missing = [v for v in _REQUIRED_ENV_VARS if not os.getenv(v)]
if _missing:
    st.error(f"Missing required environment variable(s): {', '.join(_missing)}. Please set them in your .env file.")
    sys.exit(1)

# Page config

st.set_page_config(
    page_title="Tina — Travel Planner",
    page_icon="✈️",
    layout="centered",
)

# ── Custom CSS — Dark theme ───────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Design Tokens ─────────────────────────────────────────── */
    :root {
        --bg-primary: #0f1117;
        --bg-secondary: #1a1b2e;
        --bg-surface: #1e1f35;
        --bg-card: rgba(30, 31, 53, 0.85);
        --text-primary: #e8e8ef;
        --text-secondary: #9a9ab0;
        --text-muted: #6b6b80;
        --accent-teal: #00d4aa;
        --accent-amber: #f0a500;
        --accent-blue: #4a9eff;
        --border-subtle: rgba(255, 255, 255, 0.07);
        --border-accent: rgba(0, 212, 170, 0.25);
        --glow-teal: 0 0 20px rgba(0, 212, 170, 0.08);
        --radius: 12px;
    }

    /* ── Global ────────────────────────────────────────────────── */
    html, body, .stApp, .stApp * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    .stApp {
        background: linear-gradient(160deg, var(--bg-primary) 0%, var(--bg-secondary) 60%, #141528 100%);
    }

    #MainMenu, footer, header { visibility: hidden; }

    .main .block-container {
        max-width: 800px;
        padding-top: 1rem;
        padding-bottom: 4rem;
    }

    /* ── Header Card ───────────────────────────────────────────── */
    .tina-header {
        background: var(--bg-card);
        border: 1px solid var(--border-accent);
        padding: 1.1rem 1.4rem;
        border-radius: var(--radius);
        margin-bottom: 1.2rem;
        display: flex;
        align-items: center;
        gap: 14px;
        backdrop-filter: blur(12px);
        box-shadow: var(--glow-teal);
        animation: fadeIn 0.6s ease-out;
    }
    .tina-header .icon-wrap {
        width: 46px; height: 46px;
        background: linear-gradient(135deg, rgba(0,212,170,0.2), rgba(74,158,255,0.15));
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.5rem;
    }
    .tina-header .title {
        font-size: 1.25rem; font-weight: 700;
        color: var(--text-primary); letter-spacing: 0.3px;
    }
    .tina-header .subtitle {
        font-size: 0.78rem; color: var(--accent-teal);
        font-weight: 500; display: flex; align-items: center; gap: 6px;
        margin-top: 2px;
    }
    .status-dot {
        width: 6px; height: 6px; border-radius: 50%;
        background: var(--accent-teal);
        display: inline-block;
        animation: pulse 2s ease-in-out infinite;
    }

    /* ── Chat message overrides ────────────────────────────────── */
    [data-testid="stChatMessage"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius) !important;
        animation: fadeInUp 0.35s ease-out;
    }
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] li,
    [data-testid="stChatMessage"] span,
    [data-testid="stChatMessage"] td,
    [data-testid="stChatMessage"] th {
        color: var(--text-primary) !important;
        line-height: 1.65 !important;
        font-size: 0.93rem !important;
    }
    [data-testid="stChatMessage"] strong,
    [data-testid="stChatMessage"] b {
        color: var(--accent-teal) !important;
        font-weight: 600 !important;
    }
    [data-testid="stChatMessage"] em,
    [data-testid="stChatMessage"] i {
        color: var(--text-secondary) !important;
    }
    [data-testid="stChatMessage"] h1,
    [data-testid="stChatMessage"] h2,
    [data-testid="stChatMessage"] h3 {
        color: var(--text-primary) !important;
        border-bottom: 1px solid var(--border-subtle) !important;
        padding-bottom: 0.4rem !important;
    }
    [data-testid="stChatMessage"] code {
        background: rgba(0,212,170,0.1) !important;
        color: var(--accent-teal) !important;
        padding: 0.15rem 0.4rem !important;
        border-radius: 4px !important;
    }
    [data-testid="stChatMessage"] ul {
        padding-left: 1.2rem !important;
    }

    /* ── Chat input ────────────────────────────────────────────── */
    [data-testid="stChatInput"] {
        background: transparent !important;
    }
    /* Bottom bar container — force dark background */
    [data-testid="stBottom"],
    [data-testid="stBottomBlockContainer"],
    .stChatInput,
    [data-testid="stBottom"] > div,
    [data-testid="stChatInput"] > div,
    [data-testid="stChatInputContainer"],
    .stChatInput > div {
        background: var(--bg-primary) !important;
        background-color: var(--bg-primary) !important;
        border-color: transparent !important;
    }
    [data-testid="stChatInput"] textarea {
        background: var(--bg-surface) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-accent) !important;
        border-radius: 24px !important;
        font-size: 0.93rem !important;
        padding: 0.7rem 1rem !important;
    }
    [data-testid="stChatInput"] textarea:focus {
        border-color: var(--accent-teal) !important;
        box-shadow: 0 0 0 3px rgba(0, 212, 170, 0.12) !important;
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: var(--text-muted) !important;
    }
    [data-testid="stChatInput"] button {
        background: var(--accent-teal) !important;
        color: var(--bg-primary) !important;
        border-radius: 50% !important;
    }
    [data-testid="stChatInput"] button:hover {
        background: #00e6b8 !important;
    }

    /* ── Sidebar ───────────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--bg-secondary) 0%, #12132a 100%) !important;
        border-right: 1px solid var(--border-subtle) !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdown"] p,
    [data-testid="stSidebar"] [data-testid="stMarkdown"] span,
    [data-testid="stSidebar"] [data-testid="stMarkdown"] div {
        color: var(--text-primary) !important;
    }

    /* Sidebar button */
    [data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, rgba(0,212,170,0.15), rgba(74,158,255,0.12)) !important;
        color: var(--accent-teal) !important;
        border: 1px solid var(--border-accent) !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 0.55rem 1rem !important;
        transition: all 0.25s ease !important;
        font-size: 0.9rem !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: linear-gradient(135deg, rgba(0,212,170,0.25), rgba(74,158,255,0.2)) !important;
        border-color: var(--accent-teal) !important;
        transform: translateY(-1px) !important;
        box-shadow: var(--glow-teal) !important;
    }

    /* ── Sidebar Cards ─────────────────────────────────────────── */
    .sidebar-brand {
        text-align: center;
        padding: 1.2rem 0 1rem;
    }
    .sidebar-brand .logo { font-size: 2.4rem; }
    .sidebar-brand .name {
        font-size: 1.3rem; font-weight: 700;
        color: var(--text-primary); margin-top: 0.2rem;
    }
    .sidebar-brand .tagline {
        font-size: 0.78rem; color: var(--accent-teal);
        font-weight: 500; margin-top: 0.15rem;
    }

    /* Sidebar progress bar */
    [data-testid="stSidebar"] [data-testid="stProgress"] > div {
        background: var(--border-subtle) !important;
        height: 4px !important;
        border-radius: 2px !important;
    }
    [data-testid="stSidebar"] [data-testid="stProgress"] > div > div {
        background: linear-gradient(90deg, var(--accent-teal), var(--accent-blue)) !important;
        border-radius: 2px !important;
    }
    [data-testid="stSidebar"] [data-testid="stProgress"] p {
        font-size: 0.72rem !important;
        color: var(--text-muted) !important;
    }

    /* Sidebar headings and text */
    [data-testid="stSidebar"] h5 {
        color: var(--text-primary) !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.5px !important;
    }
    [data-testid="stSidebar"] em {
        color: var(--text-muted) !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: var(--border-subtle) !important;
        margin: 0.8rem 0 !important;
    }

    .sidebar-footer {
        text-align: center; font-size: 0.68rem;
        color: var(--text-muted); line-height: 1.7;
        margin-top: 2rem; padding-top: 1rem;
        border-top: 1px solid var(--border-subtle);
    }

    /* ── Divider override ──────────────────────────────────────── */
    hr {
        border-color: var(--border-subtle) !important;
    }

    /* ── Spinner override ──────────────────────────────────────── */
    .stSpinner > div > div {
        border-top-color: var(--accent-teal) !important;
    }
    .stSpinner > div > span {
        color: var(--text-secondary) !important;
    }

    /* ── Animations ────────────────────────────────────────────── */
    @keyframes fadeIn {
        from { opacity: 0; }
        to   { opacity: 1; }
    }
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50%      { opacity: 0.35; }
    }
</style>
""", unsafe_allow_html=True)


# ── Session state init ────────────────────────────────────────────────────────

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "tina_state" not in st.session_state:
    st.session_state.tina_state = {}

if "processing" not in st.session_state:
    st.session_state.processing = False


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    # Branding
    st.markdown("""
    <div class="sidebar-brand">
        <div class="logo">✈️</div>
        <div class="name">Tina</div>
        <div class="tagline">Travel Planning Assistant</div>
    </div>
    """, unsafe_allow_html=True)

    # New Chat button
    if st.button("🔄  New Conversation", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.tina_state = {}
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

    # Trip Details Card — using native Streamlit components
    tina_state = st.session_state.tina_state
    dest = tina_state.get("destination", "")
    days = tina_state.get("days", "")
    budget = tina_state.get("budget", "")

    filled = sum(1 for x in [dest, days, budget] if x)

    st.markdown("---")
    st.markdown("##### 📋 Trip Details")

    dest_val = dest if dest else "*Not set yet*"
    days_val = f"{days} days" if days else "*Not set yet*"
    budget_val = budget.capitalize() if budget else "*Not set yet*"

    st.markdown(f"📍 **Destination** — {dest_val}")
    st.markdown(f"📅 **Duration** — {days_val}")
    st.markdown(f"💰 **Budget** — {budget_val}")

    st.progress(filled / 3, text=f"{filled}/3 details collected")

    # Footer
    st.markdown("""
    <div class="sidebar-footer">
        Tina uses real-time search<br>
        Powered by <strong style="color:#9a9ab0;">OpenAI</strong> + <strong style="color:#9a9ab0;">LangGraph</strong>
    </div>
    """, unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="tina-header">
    <div class="icon-wrap">✈️</div>
    <div>
        <div class="title">Tina</div>
        <div class="subtitle">
            <span class="status-dot"></span> Online — Ready to plan your trip
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Welcome message (first load) ──────────────────────────────────────────────

if not st.session_state.chat_history:
    welcome = (
        "Hi there! I'm **Tina** 👋 your personal travel planning assistant!\n\n"
        "I can help you:\n"
        "- 🌍 **Explore** any destination (famous places, food, culture)\n"
        "- 🗓️ **Plan** a day-by-day itinerary with nearby attractions grouped together\n"
        "- 🏨 **Find** hotels that fit your budget\n\n"
        "Just ask me anything — *\"What are the must-see places in Rajasthan?\"* "
        "or *\"I want to plan a trip to Goa\"* — and I'll take it from there! ✈️"
    )
    st.session_state.chat_history.append(("assistant", welcome))


# ── Render chat history ───────────────────────────────────────────────────────

for role, text in st.session_state.chat_history:
    avatar = "✈️" if role == "assistant" else "👤"
    with st.chat_message(role, avatar=avatar):
        st.markdown(text)


# ── Chat input (pinned to bottom) ────────────────────────────────────────────

user_input = st.chat_input("Ask Tina anything about travel...")


# ── Handle send ───────────────────────────────────────────────────────────────

if user_input and user_input.strip():
    user_text = user_input.strip()

    # Add user message to history
    st.session_state.chat_history.append(("user", user_text))

    # Display the new user message immediately
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_text)

    # Show thinking indicator while processing
    with st.chat_message("assistant", avatar="✈️"):
        with st.spinner("Tina is thinking... ✈️"):
            try:
                from graph import chat  # import here to avoid circular on load

                response_text, updated_state = chat(
                    user_message=user_text,
                    thread_id=st.session_state.thread_id,
                    current_state=st.session_state.tina_state,
                )

                # Save updated state (trip details persist across turns)
                st.session_state.tina_state = updated_state

                # Add Tina's response
                st.session_state.chat_history.append(("assistant", response_text))

            except Exception as e:
                error_msg = "Oops! Something went wrong. Please try again or start a new conversation."
                st.session_state.chat_history.append(("assistant", error_msg))

    st.rerun()

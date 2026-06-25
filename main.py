"""
main.py
-------
Streamlit UI for Tina — Travel Planning Chatbot.
Clean chat window. Memory is maintained per session via LangGraph MemorySaver.
"""

import streamlit as st
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Tina — Travel Planner",
    page_icon="✈️",
    layout="centered",
)

# ── Custom CSS — clean, travel-themed ────────────────────────────────────────

st.markdown("""
<style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #f0f7ff 0%, #e8f4f8 100%);
    }

    /* Hide Streamlit default header/footer */
    #MainMenu, footer, header { visibility: hidden; }

    /* Chat container */
    .main .block-container {
        max-width: 760px;
        padding-top: 1rem;
        padding-bottom: 6rem;
    }

    /* Title bar */
    .tina-header {
        background: linear-gradient(90deg, #1a73e8, #0d47a1);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    /* User message bubble */
    .user-bubble {
        background: #1a73e8;
        color: white;
        padding: 0.75rem 1rem;
        border-radius: 18px 18px 4px 18px;
        margin: 0.5rem 0 0.5rem 20%;
        word-wrap: break-word;
        font-size: 0.95rem;
        line-height: 1.5;
    }

    /* Assistant message bubble */
    .tina-bubble {
        background: white;
        color: #1a1a2e;
        padding: 0.75rem 1rem;
        border-radius: 18px 18px 18px 4px;
        margin: 0.5rem 20% 0.5rem 0;
        word-wrap: break-word;
        font-size: 0.95rem;
        line-height: 1.6;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        border-left: 3px solid #1a73e8;
    }

    /* Thinking indicator */
    .thinking {
        color: #888;
        font-style: italic;
        font-size: 0.85rem;
        padding: 0.5rem 1rem;
    }

    /* Trip details pill */
    .trip-pill {
        display: inline-block;
        background: #e8f0fe;
        color: #1a73e8;
        padding: 0.2rem 0.7rem;
        border-radius: 20px;
        font-size: 0.8rem;
        margin: 0.2rem;
        border: 1px solid #c5d8fd;
    }

    /* Input area override */
    .stTextInput input {
        border-radius: 24px !important;
        border: 2px solid #1a73e8 !important;
        padding: 0.6rem 1rem !important;
        font-size: 0.95rem !important;
    }
    .stTextInput input:focus {
        box-shadow: 0 0 0 3px rgba(26,115,232,0.15) !important;
    }
</style>
""", unsafe_allow_html=True)


# ── Session state init ────────────────────────────────────────────────────────

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []   # list of (role, text) for display

if "tina_state" not in st.session_state:
    st.session_state.tina_state = {}     # LangGraph state (trip details + memory)

if "processing" not in st.session_state:
    st.session_state.processing = False


# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="tina-header">
    <span style="font-size:2rem">✈️</span>
    <div>
        <div style="font-size:1.3rem; font-weight:700; letter-spacing:0.5px">Tina</div>
        <div style="font-size:0.8rem; opacity:0.85">Your AI Travel Planning Assistant</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Show collected trip details (if any) ─────────────────────────────────────

tina_state = st.session_state.tina_state
has_details = any([
    tina_state.get("destination"),
    tina_state.get("days"),
    tina_state.get("budget"),
])

if has_details:
    pills_html = '<div style="margin-bottom:1rem; padding: 0.5rem 0;">'
    if tina_state.get("destination"):
        pills_html += f'<span class="trip-pill">📍 {tina_state["destination"]}</span>'
    if tina_state.get("days"):
        pills_html += f'<span class="trip-pill">📅 {tina_state["days"]} days</span>'
    if tina_state.get("budget"):
        pills_html += f'<span class="trip-pill">💰 {tina_state["budget"]}</span>'
    pills_html += '</div>'
    st.markdown(pills_html, unsafe_allow_html=True)


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
    if role == "user":
        st.markdown(f'<div class="user-bubble">{text}</div>', unsafe_allow_html=True)
    else:
        # Convert markdown bold/newlines for HTML display
        html_text = text.replace("\n", "<br>").replace("**", "<b>", 1)
        st.markdown(f'<div class="tina-bubble">{text}</div>', unsafe_allow_html=True)


# ── Input form ────────────────────────────────────────────────────────────────

with st.form(key="chat_form", clear_on_submit=True):
    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input(
            label="message",
            placeholder="Ask Tina anything about travel...",
            label_visibility="collapsed",
        )
    with col2:
        send = st.form_submit_button("Send ➤", use_container_width=True)


# ── Handle send ───────────────────────────────────────────────────────────────

if send and user_input.strip():
    user_text = user_input.strip()

    # Add user message to display
    st.session_state.chat_history.append(("user", user_text))

    # Show thinking indicator while processing
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
            error_msg = f"Oops! Something went wrong: {str(e)}\n\nPlease check your API keys in the `.env` file."
            st.session_state.chat_history.append(("assistant", error_msg))

    st.rerun()


# ── Reset button ─────────────────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)
col_a, col_b, col_c = st.columns([3, 1, 3])
with col_b:
    if st.button("🔄 Reset", help="Start a new conversation"):
        st.session_state.chat_history = []
        st.session_state.tina_state = {}
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()


# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown("""
<div style="text-align:center; color:#aaa; font-size:0.75rem; margin-top:2rem;">
    Tina uses real-time search • Powered by OpenAI + LangGraph
</div>
""", unsafe_allow_html=True)

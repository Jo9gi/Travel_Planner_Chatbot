"""
agents/supervisor.py
--------------------
Tina's brain — the Supervisor node.

Decides one of 3 modes per user message:
  MODE 1 — direct_answer : Simple Q&A → Tavily search → respond
  MODE 2 — gather_info   : User wants to plan → collect details conversationally
  MODE 3 — full_plan     : All details ready → run sequential agents

Also writes the final friendly response back to the user.
"""

import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from tools.tavily_tool import tavily_search


# ── LLM setup ────────────────────────────────────────────────────────────────

def get_llm():
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0.3,
        api_key=os.getenv("OPENAI_API_KEY"),
    )


# ── System prompt for Tina ───────────────────────────────────────────────────

TINA_SYSTEM = """You are Tina, a friendly and knowledgeable travel planning assistant.
Your personality: warm, enthusiastic about travel, concise, and helpful.

You have access to real-time search results and travel planning tools.
NEVER make up facts about destinations — always base answers on provided search results.
If search results are provided, use them. If not, say you'll look it up.

You understand 3 types of user requests:
1. Simple travel questions → answer using search results only
2. User wants to plan a trip → collect: destination, days, budget, travel style
3. Full plan request (all info available) → present the complete itinerary

Always be conversational and friendly. Use emojis occasionally 🌍✈️🏨.
When gathering info for a trip plan, ask ONE question at a time, not all at once.
"""


# ── Mode classifier ──────────────────────────────────────────────────────────

CLASSIFIER_PROMPT = """Analyze this user message and conversation history.
Classify the intent as exactly one of:
- "direct_answer"  : User asks a factual travel question (places, tips, costs, weather, etc.)
- "gather_info"    : User expresses intent to travel/plan but hasn't provided all details
- "full_plan"      : User provides or modifies trip details, or explicitly asks for the plan.
- "chitchat"       : Greeting, thanks, general conversation not about travel planning

Also extract any NEW or MODIFIED trip details from the latest message. If the user modifies a value (e.g., adding a day), calculate the new total based on the conversation history. If a detail is not mentioned or changed in the latest message, leave it null.
- destination: string or null
- days: integer or null  
- budget: "budget" | "mid-range" | "luxury" | null

Respond ONLY with valid JSON, no explanation:
{"mode": "...", "destination": ..., "days": ..., "budget": ...}
"""


def classify_intent(messages: list, user_message: str) -> dict:
    """Use LLM to classify user intent and extract trip details."""
    llm = get_llm()

    # Build context from last 6 messages
    history_text = ""
    for m in messages[-6:]:
        role = m.get("role", "")
        content = m.get("content", "")
        history_text += f"{role}: {content}\n"

    classify_messages = [
        SystemMessage(content=CLASSIFIER_PROMPT),
        HumanMessage(content=f"Conversation so far:\n{history_text}\n\nLatest user message: {user_message}")
    ]

    try:
        result = llm.invoke(classify_messages)
        # Strip potential markdown formatting from json response
        content = result.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        parsed = json.loads(content.strip())
        return parsed
    except Exception:
        # Safe fallback
        return {"mode": "direct_answer", "destination": None, "days": None, "budget": None}


# ── Check if we have all info needed for full plan ───────────────────────────

def has_all_trip_details(state: dict) -> bool:
    """Returns True only if destination, days, and budget are all known."""
    return (
        bool(state.get("destination"))
        and bool(state.get("days"))
        and bool(state.get("budget"))
    )


# ── Response generator ───────────────────────────────────────────────────────

def generate_response(state: dict, mode: str, search_result: str = "") -> str:
    """Generate Tina's final friendly response to the user."""
    llm = get_llm()

    messages = state.get("messages", [])
    destination = state.get("destination", "")
    days = state.get("days", "")
    budget = state.get("budget", "")
    day_plan = state.get("day_plan", "")

    # Build LLM message history
    lc_messages = [SystemMessage(content=TINA_SYSTEM)]
    for m in messages[:-1]:   # all except current (we handle it below)
        if m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_messages.append(AIMessage(content=m["content"]))

    # Add context depending on mode
    user_msg = messages[-1]["content"] if messages else ""

    trip_context = ""
    if day_plan:
        trip_context = f"\n\nCurrent Trip Plan Context:\n{day_plan}\n"

    if mode == "direct_answer" and search_result:
        context = (
            f"User asked: {user_msg}\n\n"
            f"Real-time search results (use these, do not hallucinate):\n{search_result}\n"
            f"{trip_context}"
            f"Give a helpful, friendly answer based ONLY on the above search results and the current trip plan."
        )

    elif mode == "gather_info":
        missing = []
        if not destination:
            missing.append("destination")
        if not days:
            missing.append("number of days")
        if not budget:
            missing.append("budget (budget/mid-range/luxury)")

        context = (
            f"User message: {user_msg}\n\n"
            f"Trip details collected so far:\n"
            f"  Destination: {destination or 'not yet'}\n"
            f"  Days: {days or 'not yet'}\n"
            f"  Budget: {budget or 'not yet'}\n\n"
            f"Still need: {', '.join(missing)}\n\n"
            f"Respond warmly and ask for the FIRST missing detail only. "
            f"If destination just mentioned, show enthusiasm and ask for days."
        )

    elif mode == "full_plan":
        destination_info = state.get("destination_info", "")
        hotel_info = state.get("hotel_info", "")

        context = (
            f"User wants a complete trip plan. All details collected:\n"
            f"  Destination: {destination}\n"
            f"  Days: {days}\n"
            f"  Budget: {budget}\n\n"
            f"--- Destination Research ---\n{destination_info[:2000]}\n\n"
            f"--- Day-by-Day Itinerary (geo-clustered) ---\n{day_plan}\n\n"
            f"--- Hotel Options ---\n{hotel_info[:2000]}\n\n"
            f"Create a complete, friendly, well-structured trip plan using ONLY the above data. "
            f"Format with clear Day 1, Day 2... sections. Include hotel suggestions and tips. "
            f"Do not invent any places or hotels not mentioned in the data."
        )

    else:  # chitchat
        context = f"User said: {user_msg}\n{trip_context}\nRespond as Tina, friendly travel assistant. Answer any questions about the trip plan using the provided context."

    lc_messages.append(HumanMessage(content=context))

    response = llm.invoke(lc_messages)
    return response.content


# ── Main supervisor node ─────────────────────────────────────────────────────

def supervisor(state: dict) -> dict:
    """
    Main entry node. Decides mode, optionally does quick search,
    and writes the assistant response.
    Does NOT call planning agents directly — graph edges handle that.
    """
    messages = state.get("messages", [])
    if not messages:
        return {**state, "next": "end", "response": "Hi! I'm Tina, your travel assistant! ✈️ Where would you like to go?"}

    user_message = messages[-1]["content"]

    # Classify intent
    classification = classify_intent(messages, user_message)
    mode = classification.get("mode", "direct_answer")

    # Update state with any newly extracted trip details
    updated_state = dict(state)
    details_updated = False
    
    if classification.get("destination"):
        updated_state["destination"] = classification["destination"]
        details_updated = True
    if classification.get("days"):
        updated_state["days"] = int(classification["days"])
        details_updated = True
    if classification.get("budget"):
        updated_state["budget"] = classification["budget"]
        details_updated = True

    print(f"[Supervisor] Mode: {mode} | Destination: {updated_state.get('destination')} | Days: {updated_state.get('days')} | Budget: {updated_state.get('budget')} | Updated: {details_updated}")

    has_existing_plan = bool(updated_state.get("day_plan"))

    # ── MODE 1: Direct answer ─────────────────────────────────────────────────
    if mode == "direct_answer":
        search_result = tavily_search(user_message)
        response = generate_response(updated_state, "direct_answer", search_result)
        return {**updated_state, "next": "end", "response": response}

    # ── MODE 2: Chitchat ──────────────────────────────────────────────────────
    if mode == "chitchat":
        response = generate_response(updated_state, "chitchat")
        return {**updated_state, "next": "end", "response": response}

    # ── MODE 3: Gather Info or Full Plan ──────────────────────────────────────
    if mode in ["gather_info", "full_plan"]:
        if has_all_trip_details(updated_state):
            # If we don't have a plan yet, OR if the user updated the trip details, we must generate a new plan.
            if not has_existing_plan or details_updated:
                print("[Supervisor] Routing to full plan agents to build/rebuild the itinerary.")
                return {**updated_state, "next": "run_agents"}
            else:
                # We already have a plan and no details were changed. Just converse.
                response = generate_response(updated_state, "chitchat")
                return {**updated_state, "next": "end", "response": response}
        else:
            response = generate_response(updated_state, "gather_info")
            return {**updated_state, "next": "end", "response": response}

    # Fallback
    response = generate_response(updated_state, "chitchat")
    return {**updated_state, "next": "end", "response": response}


# ── Final response node (after agents finish) ─────────────────────────────────

def finalize_plan(state: dict) -> dict:
    """
    Called after all 3 planning agents complete.
    Generates the full trip plan response.
    """
    response = generate_response(state, "full_plan")
    return {**state, "response": response, "next": "end"}

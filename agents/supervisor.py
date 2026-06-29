import os
import re
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from tools.tavily_tool import tavily_search

# Input sanitization 
_MAX_INPUT_LEN = 1000
def sanitize_input(text: str) -> str:
    """Strip control characters and enforce length limit to prevent prompt injection."""
    text = text.strip()[:_MAX_INPUT_LEN]
    text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)
    return text


# ── LLM setup 

def get_llm():
    return ChatOpenAI(model="gpt-4o", temperature=0.2, api_key=os.getenv("OPENAI_API_KEY"))


# ── System prompt 

TINA_SYSTEM = """You are Tina, a friendly and knowledgeable travel planning assistant.
Your personality: warm, enthusiastic about travel, concise, and helpful.
NEVER make up facts about destinations.
When gathering info for a trip plan, ask ONE question at a time, not all at once."""


# ── Classifier prompt 

CLASSIFIER_PROMPT = """Analyze this user message and conversation history.
Classify the intent as exactly one of: "direct_answer", "gather_info", "full_plan", "follow_up", or "chitchat".

- "direct_answer"  : User asks a general travel question unrelated to their current itinerary.
- "gather_info"    : User wants a full trip plan but hasn't provided all details yet.
- "full_plan"      : User provides or confirms all trip details (destination + days + budget).
- "follow_up"      : CRITICAL: User asks to modify the itinerary, asks for hotels, or asks questions about the ALREADY GENERATED trip plan.
- "chitchat"       : Greeting, thanks, or general conversation not about travel.

Extract trip details from the message.
CRITICAL: If the user provides a specific monetary budget (e.g., "10000", "500 dollars"),
extract it into 'exact_budget' AND categorize it into 'budget'.

- destination: string or null
- days: integer or null
- budget: "budget" | "mid-range" | "luxury" | null
- exact_budget: string (e.g., "10000 INR", "$500") or null

Respond ONLY with valid JSON:
{"mode": "...", "destination": "...", "days": ..., "budget": "...", "exact_budget": "..."}"""


# ── Intent classifier 

def classify_intent(messages: list, user_message: str) -> dict:
    """Use LLM to classify user intent and extract trip details."""
    llm = get_llm()
    history_text = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in messages[-6:]])

    try:
        result = llm.invoke([
            SystemMessage(content=CLASSIFIER_PROMPT),
            HumanMessage(content=f"History:\n{history_text}\n\nLatest: {user_message}")
        ])
        content = result.content.strip().strip("`").removeprefix("json").strip()
        return json.loads(content)
    except Exception:
        return {"mode": "direct_answer", "destination": None, "days": None, "budget": None, "exact_budget": None}


# ── State helpers 

def has_all_trip_details(state: dict) -> bool:
    return bool(state.get("destination")) and bool(state.get("days")) and bool(state.get("budget"))


def _build_message_history(messages: list) -> list:
    lc_messages = [SystemMessage(content=TINA_SYSTEM)]
    for m in messages[:-1]:
        if m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_messages.append(AIMessage(content=m["content"]))
    return lc_messages


# ── Context builders 

def _build_full_plan_context(state: dict) -> str:
    dest = state.get("destination")
    days = state.get("days")
    budget = state.get("budget")
    exact_budget = state.get("exact_budget")

    budget_guardrail = ""
    if exact_budget:
        budget_guardrail = (
            f"\nCRITICAL BUDGET RULE: The user has a STRICT TOTAL budget of {exact_budget} "
            f"for the ENTIRE {days}-day trip. Do the math: "
            f"(Accommodation/night × {days}) + (Food & Transport/day × {days}) "
            f"MUST be less than {exact_budget}. Suggest hostels or budget stays if needed."
        )

    return (
        f"Create a {days}-day trip plan for {dest}. Budget tier: {budget}.{budget_guardrail}\n\n"
        f"--- Destination Info ---\n{state.get('destination_info', '')[:2000]}\n\n"
        f"--- Raw POI Clusters ---\n{state.get('day_plan', '')}\n\n"
        f"--- Hotel Data ---\n{state.get('hotel_info', '')[:3000]}\n\n"
        f"CRITICAL RULES FOR GENERATION:\n"
        f"1. GEOGRAPHY: Cross-check every fact. Do NOT invent beaches in landlocked cities or landmarks that don't exist.\n"
        f"2. CULLING: The raw POI data contains noise — residential colony parks, corporate office buildings, "
        f"and random street statues. DO NOT include these. Only include major tourist, historical, cultural, "
        f"or well-known natural attractions.\n"
        f"3. FORMAT: Write a friendly, readable day-by-day itinerary with hotel suggestions and realistic budget breakdown."
    )


def _build_gather_info_context(state: dict, user_msg: str) -> str:
    missing = [
        k for k, v in {
            "destination": state.get("destination"),
            "days": state.get("days"),
            "budget": state.get("budget"),
        }.items() if not v
    ]
    return (
        f"User said: {user_msg}\n"
        f"Collected — destination: {state.get('destination') or 'not yet'}, "
        f"days: {state.get('days') or 'not yet'}, budget: {state.get('budget') or 'not yet'}\n"
        f"Still need: {', '.join(missing)}. Ask warmly for the FIRST missing detail only."
    )


# ── Response generator 

def generate_response(state: dict, mode: str, search_result: str = "") -> str:
    llm = get_llm()
    messages = state.get("messages", [])
    user_msg = messages[-1]["content"] if messages else ""
    lc_messages = _build_message_history(messages)

    if mode == "full_plan":
        context = _build_full_plan_context(state)
    elif mode == "follow_up":
        context = (
            f"User asked a follow-up question about their trip: {user_msg}\n\n"
            f"Here is the current trip plan context to help you answer:\n"
            f"--- Destination ---\n{state.get('destination')}\n"
            f"--- Current Day Plan ---\n{state.get('day_plan', 'No plan generated yet.')}\n"
            f"--- Hotel Data ---\n{state.get('hotel_info', 'No hotels found yet.')}\n\n"
            f"CRITICAL RULES:\n"
            f"1. ANTI-LAZINESS: NEVER tell the user to 'check booking platforms', 'use Expedia', or 'search online' themselves. You are their planner; you do the work.\n"
            f"2. Look at the 'Hotel Data' or 'Day Plan' provided above. Suggest specific options from that exact list that best fit their question."
        )
    elif mode == "gather_info":
        context = _build_gather_info_context(state, user_msg)
    elif mode == "direct_answer" and search_result:
        context = (
            f"User asked: {user_msg}\n\n"
            f"Real-time search results (use these, do not hallucinate):\n{search_result}\n\n"
            f"Give a helpful, friendly answer based ONLY on the above search results."
        )
    else:
        context = f"User said: {user_msg}\nRespond as Tina, a friendly travel assistant."

    lc_messages.append(HumanMessage(content=context))
    return llm.invoke(lc_messages).content


# ── Main supervisor node 

def supervisor(state: dict) -> dict:
    messages = state.get("messages", [])
    if not messages:
        return {**state, "next": "end", "response": "Hi! I'm Tina, your travel assistant! Where would you like to go?"}

    user_msg = sanitize_input(messages[-1]["content"])
    classification = classify_intent(messages, user_msg)
    mode = classification.get("mode", "direct_answer")

    updated = dict(state)
    details_changed = False

    for key in ["destination", "days", "budget", "exact_budget"]:
        if classification.get(key):
            updated[key] = classification[key]
            details_changed = True

    print(f"[Supervisor] mode={mode} | dest={updated.get('destination')} | days={updated.get('days')} | budget={updated.get('budget')} | exact={updated.get('exact_budget')}")

    # Follow-up about existing itinerary
    if mode == "follow_up":
        return {**updated, "next": "end", "response": generate_response(updated, "follow_up")}

    # Direct answer with destination appended to search query
    if mode == "direct_answer":
        dest_context = f" in {updated.get('destination')}" if updated.get("destination") else ""
        search_result = tavily_search(user_msg + dest_context)
        return {**updated, "next": "end", "response": generate_response(updated, "direct_answer", search_result)}

    # Chitchat
    if mode == "chitchat":
        return {**updated, "next": "end", "response": generate_response(updated, "chitchat")}

    # Gather info or full plan
    if mode in ["gather_info", "full_plan"]:
        if has_all_trip_details(updated):
            if not updated.get("day_plan") or details_changed:
                print("[Supervisor] Routing to agents.")
                return {**updated, "next": "run_agents"}
            return {**updated, "next": "end", "response": generate_response(updated, "chitchat")}
        return {**updated, "next": "end", "response": generate_response(updated, "gather_info")}

    # Fallback
    return {**updated, "next": "end", "response": generate_response(updated, "chitchat")}


# ── Finalize plan node 

def finalize_plan(state: dict) -> dict:
    return {**state, "response": generate_response(state, "full_plan"), "next": "end"}

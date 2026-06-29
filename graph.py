from typing import TypedDict, Optional, List
from concurrent.futures import ThreadPoolExecutor
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agents.supervisor import supervisor, finalize_plan
from agents.destination import destination_researcher
from agents.day_planner import day_planner
from agents.hotel import hotel_researcher


# ── State schema ──────────────────────────────────────────────────────────────

class TinaState(TypedDict):
    # Conversation history: list of {"role": "user"/"assistant", "content": "..."}
    messages: List[dict]

    # Trip details (filled progressively by supervisor)
    destination: Optional[str]
    days: Optional[int]
    budget: Optional[str]        # "budget", "mid-range", "luxury"
    exact_budget: Optional[str]  # e.g., "10000 INR", "$500"

    # Agent outputs
    destination_info: Optional[str]
    day_plan: Optional[str]
    hotel_info: Optional[str]

    # Routing signal set by supervisor
    next: Optional[str]

    # Final response text to send to UI
    response: Optional[str]


# ── Parallel runner node ─────────────────────────────────────────────────────

def parallel_researchers(state: TinaState) -> dict:
    """Run all 3 research agents simultaneously using threads."""
    with ThreadPoolExecutor(max_workers=3) as executor:
        f_dest  = executor.submit(destination_researcher, state)
        f_day   = executor.submit(day_planner, state)
        f_hotel = executor.submit(hotel_researcher, state)

        dest_result  = f_dest.result()
        day_result   = f_day.result()
        hotel_result = f_hotel.result()

    return {
        **state,
        "destination_info": dest_result.get("destination_info"),
        "day_plan":         day_result.get("day_plan"),
        "hotel_info":       hotel_result.get("hotel_info"),
    }


# ── Routing function ──────────────────────────────────────────────────────────

def route_after_supervisor(state: TinaState) -> str:
    return state.get("next", "end")


# ── Build the graph ───────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(TinaState)

    # Register all nodes
    graph.add_node("supervisor", supervisor)
    graph.add_node("parallel_researchers", parallel_researchers)
    graph.add_node("finalize_plan", finalize_plan)

    # Entry point
    graph.set_entry_point("supervisor")

    # Conditional routing from supervisor
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "run_agents": "parallel_researchers",
            "end": END,
        }
    )

    graph.add_edge("parallel_researchers", "finalize_plan")
    graph.add_edge("finalize_plan", END)

    # Compile with memory (MemorySaver = in-memory checkpointing per thread_id)
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


# ── Singleton graph instance ──────────────────────────────────────────────────

tina_graph = build_graph()


# ── Helper to invoke graph from UI ───────────────────────────────────────────

def chat(user_message: str, thread_id: str, current_state: dict = None) -> tuple[str, dict]:
    """
    Send a user message to Tina and get a response.

    Args:
        user_message: The user's input text
        thread_id:    Session ID (one per browser session for memory)
        current_state: Pass existing state to preserve trip details across turns

    Returns:
        (assistant_response, updated_state)
    """
    config = {"configurable": {"thread_id": thread_id}}

    # Build input state — append new user message to history
    messages = (current_state or {}).get("messages", [])
    messages = messages + [{"role": "user", "content": user_message}]

    input_state = {
        **(current_state or {}),
        "messages": messages,
        "response": None,
        "next": None,
        "destination_info": None,
        "day_plan": (current_state or {}).get("day_plan"),
        "hotel_info": None,
    }

    # Run the graph
    result = tina_graph.invoke(input_state, config=config)

    # Extract response
    response_text = result.get("response", "Sorry, I had trouble processing that. Could you try again?")

    # Append assistant response to message history
    result["messages"] = result.get("messages", []) + [
        {"role": "assistant", "content": response_text}
    ]

    return response_text, result

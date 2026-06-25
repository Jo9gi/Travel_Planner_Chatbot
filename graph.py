"""
graph.py
--------
LangGraph StateGraph for Tina.

Flow:
  supervisor → (end | destination_researcher → day_planner → hotel_researcher → finalize)

Memory: MemorySaver checkpoints the full state per thread_id,
        so Tina remembers the whole conversation.
"""

from typing import TypedDict, Optional, List
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
    budget: Optional[str]

    # Agent outputs
    destination_info: Optional[str]
    day_plan: Optional[str]
    hotel_info: Optional[str]

    # Routing signal set by supervisor
    next: Optional[str]

    # Final response text to send to UI
    response: Optional[str]


# ── Routing function ──────────────────────────────────────────────────────────

def route_after_supervisor(state: TinaState) -> str:
    """
    Read state['next'] and decide which node to go to.
    'run_agents' → start the sequential planning pipeline
    'end'        → done, return to user
    """
    return state.get("next", "end")


# ── Build the graph ───────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(TinaState)

    # Register all nodes
    graph.add_node("supervisor", supervisor)
    graph.add_node("destination_researcher", destination_researcher)
    graph.add_node("day_planner", day_planner)
    graph.add_node("hotel_researcher", hotel_researcher)
    graph.add_node("finalize_plan", finalize_plan)

    # Entry point
    graph.set_entry_point("supervisor")

    # Conditional routing from supervisor
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "run_agents": "destination_researcher",   # full plan → agents
            "end": END,                               # simple answer → done
        }
    )

    # Sequential agent pipeline
    graph.add_edge("destination_researcher", "day_planner")
    graph.add_edge("day_planner", "hotel_researcher")
    graph.add_edge("hotel_researcher", "finalize_plan")
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

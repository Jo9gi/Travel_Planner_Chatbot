"""
agents/destination.py
---------------------
Destination Researcher agent.
Searches real-time info about a destination using Tavily.
Called in Mode 3 (full trip plan) by the supervisor.
"""

from tools.tavily_tool import tavily_search


def destination_researcher(state: dict) -> dict:
    """
    Gathers comprehensive destination info:
    - Famous places / attractions
    - Best time to visit
    - Local tips, culture, food
    - Weather overview

    Updates state with 'destination_info'.
    """
    destination = state.get("destination", "")
    days = state.get("days", 3)

    if not destination:
        return {**state, "destination_info": "No destination specified."}

    # Search 1: General destination overview
    overview = tavily_search(
        f"travel guide {destination} top attractions things to do tourist places"
    )

    # Search 2: Practical tips
    tips = tavily_search(
        f"{destination} travel tips best time to visit local food culture"
    )

    destination_info = (
        f"=== Destination Research: {destination} ===\n\n"
        f"--- Overview & Attractions ---\n{overview}\n\n"
        f"--- Travel Tips & Culture ---\n{tips}"
    )

    print(f"[Destination Researcher] Completed research for: {destination}")

    return {**state, "destination_info": destination_info}

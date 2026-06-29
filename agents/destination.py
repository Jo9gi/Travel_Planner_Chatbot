from tools.tavily_tool import tavily_search

def destination_researcher(state: dict) -> dict:
    destination = state.get("destination", "")
    days = state.get("days", 3)

    if not destination:
        return {**state, "destination_info": "No destination specified."}

    # Single combined search — halves Tavily latency vs two separate calls
    research = tavily_search(
        f"travel guide {destination} top attractions things to do tourist places, "
        f"travel tips best time to visit local food culture",
        max_results=6
    )

    destination_info = (
        f"=== Destination Research: {destination} ===\n\n"
        f"{research}"
    )
    
    print(f"[Destination Researcher] Completed research for: {destination}")

    return {**state, "destination_info": destination_info}

from tools.maps_tool import build_day_clusters

def day_planner(state: dict) -> dict:

    destination = state.get("destination", "")
    days = state.get("days", 3)

    if not destination:
        return {**state, "day_plan": "No destination to plan for."}

    print(f"[Day Planner] Building {days}-day plan for: {destination}")

    clusters = build_day_clusters(city=destination, num_days=days)

    day_plan = (
        f"=== {days}-Day Itinerary Clusters: {destination} ===\n\n"
        f"{clusters}\n\n"
        f"Note: Places are grouped by proximity to minimise travel time."
    )

    return {**state, "day_plan": day_plan}

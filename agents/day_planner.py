"""
agents/day_planner.py
---------------------
Day Planner agent.
Uses Nominatim + Overpass API to cluster nearby attractions
into a logical day-by-day itinerary.
Called after Destination Researcher in Mode 3.
"""

from tools.maps_tool import build_day_clusters


def day_planner(state: dict) -> dict:
    """
    Builds a geo-clustered day plan:
    - Fetches real POIs from OpenStreetMap (Overpass)
    - Groups nearby places together per day
    - Returns a structured itinerary text

    Updates state with 'day_plan'.
    """
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

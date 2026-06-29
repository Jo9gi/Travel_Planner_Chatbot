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


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    # Step 1: Test with valid destination
    print("=== Step 1: Valid destination ===")
    state = {"destination": "Vizag", "days": 3}
    result = day_planner(state)
    print(f"day_plan length: {len(result.get('day_plan', ''))} chars")
    print(f"Output:\n{result.get('day_plan', '')}")

    # Step 2: Test with missing destination
    print("\n=== Step 2: Missing destination ===")
    result = day_planner({})
    print(f"Output: {result.get('day_plan')}")

    # Step 3: Test with different days
    print("\n=== Step 3: 5-day plan ===")
    result = day_planner({"destination": "Rajamahendravaram", "days": 5})
    print(f"Output:\n{result.get('day_plan', '')}")

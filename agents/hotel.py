from tools.hotel_tool import research_hotels

def hotel_researcher(state: dict) -> dict:

    destination = state.get("destination", "")
    budget = state.get("budget", "any")

    if not destination:
        return {**state, "hotel_info": "No destination for hotel search."}

    print(f"[Hotel Researcher] Searching hotels in: {destination} (budget: {budget})")

    hotel_data = research_hotels(city=destination, budget=budget)

    hotel_info = (
        f"=== Hotel Research: {destination} (Budget: {budget}) ===\n\n"
        f"{hotel_data}"
    )

    return {**state, "hotel_info": hotel_info}

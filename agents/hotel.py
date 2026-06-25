"""
agents/hotel.py
---------------
Hotel Researcher agent.
Scrapes real hotel data using Firecrawl (web scraping)
and geopy for location context.
Called last in Mode 3 sequential pipeline.
"""

from tools.hotel_tool import research_hotels


def hotel_researcher(state: dict) -> dict:
    """
    Finds real hotels near the destination:
    - Uses Firecrawl to scrape Google Hotels / Booking.com
    - Filters by budget preference if provided
    - Returns raw hotel data for supervisor to summarise

    Updates state with 'hotel_info'.
    """
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

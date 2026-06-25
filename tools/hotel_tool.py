"""
tools/hotel_tool.py
-------------------
Scrapes hotel info near a destination using Firecrawl.
geopy/Nominatim used to get precise coordinates for the area.
"""

import os
import requests
from geopy.geocoders import Nominatim

FIRECRAWL_URL = "https://api.firecrawl.dev/v1/scrape"


# ── Helper: get coordinates ───────────────────────────────────────────────────

def get_coordinates(city: str) -> tuple[float, float] | None:
    """Return (lat, lon) for a city using geopy + Nominatim."""
    geolocator = Nominatim(user_agent="TinaTravelBot/1.0")
    try:
        location = geolocator.geocode(city, timeout=10)
        if location:
            return (location.latitude, location.longitude)
    except Exception:
        pass
    return None


# ── Scrape hotel listings via Firecrawl ───────────────────────────────────────

def scrape_hotels(city: str, budget: str = "any") -> str:
    """
    Use Firecrawl to scrape hotel search results for a city.
    Budget hint: 'budget', 'mid-range', 'luxury', or 'any'.
    Returns cleaned markdown text with hotel info.
    """
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        return "Firecrawl API key not configured."

    # Build a targeted search URL (Google Hotels / Booking.com)
    budget_query = {
        "budget": "cheap hotels under 1000",
        "mid-range": "best hotels 2000 to 5000",
        "luxury": "luxury 5 star hotels",
    }.get(budget.lower(), "best hotels")

    search_url = (
        f"https://www.google.com/travel/hotels/{city.replace(' ', '-')}"
        f"?q={budget_query}+{city.replace(' ', '+')}"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "url": search_url,
        "formats": ["markdown"],
        "onlyMainContent": True,
    }

    try:
        resp = requests.post(FIRECRAWL_URL, json=payload, headers=headers, timeout=30)
        data = resp.json()

        if data.get("success") and data.get("data", {}).get("markdown"):
            raw = data["data"]["markdown"]
            # Trim to reasonable length for LLM context
            return raw[:4000]
        else:
            # Fallback: scrape Booking.com
            return _scrape_booking(city, budget_query, api_key)

    except Exception as e:
        return f"Hotel search failed: {str(e)}"


def _scrape_booking(city: str, budget_query: str, api_key: str) -> str:
    """Fallback scrape from Booking.com if Google fails."""
    url = f"https://www.booking.com/searchresults.html?ss={city.replace(' ', '+')}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True,
    }

    try:
        resp = requests.post(FIRECRAWL_URL, json=payload, headers=headers, timeout=30)
        data = resp.json()
        if data.get("success") and data.get("data", {}).get("markdown"):
            return data["data"]["markdown"][:4000]
    except Exception:
        pass

    return f"Could not retrieve hotel data for {city}. Try searching booking.com or makemytrip.com manually."


# ── Main entry point used by Hotel Researcher agent ──────────────────────────

def research_hotels(city: str, budget: str = "any") -> str:
    """
    Full pipeline: get coords + scrape hotels.
    Returns formatted text for the LLM to summarise.
    """
    coords = get_coordinates(city)
    coord_info = ""
    if coords:
        coord_info = f"(Coordinates: {coords[0]:.4f}°N, {coords[1]:.4f}°E)\n\n"

    hotel_data = scrape_hotels(city, budget)
    return f"Hotels near {city} {coord_info}{hotel_data}"

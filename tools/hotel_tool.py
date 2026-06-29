"""
tools/hotel_tool.py
-------------------
Uses Firecrawl's native /v1/search endpoint to find hotel information.
geopy/Nominatim is used to get precise coordinates for the area.
"""

import os
import logging
import requests
from geopy.geocoders import Nominatim

logger = logging.getLogger(__name__)

# Upgraded to the Search endpoint
FIRECRAWL_URL = "https://api.firecrawl.dev/v1/search"


# ── Helper: get coordinates ───────────────────────────────────────────────────

def get_coordinates(city: str) -> tuple[float, float] | None:
    """Return (lat, lon) for a city using geopy + Nominatim."""
    geolocator = Nominatim(user_agent="TinaTravelBot/2.0")
    try:
        location = geolocator.geocode(city, timeout=10)
        if location:
            return (location.latitude, location.longitude)
    except Exception:
        pass
    return None


# ── Main entry point used by Hotel Researcher agent ──────────────────────────

def research_hotels(city: str, budget: str = "any") -> str:
    """
    Full pipeline: get coords + search the web for hotels via Firecrawl.
    Returns clean markdown text for the LLM to summarise.
    """
    coords = get_coordinates(city)
    coord_info = ""
    if coords:
        coord_info = f"(Coordinates: {coords[0]:.4f}°N, {coords[1]:.4f}°E)\n\n"

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        logger.warning("FIRECRAWL_API_KEY not set — hotel search unavailable.")
        return "Hotel search is unavailable. Please configure FIRECRAWL_API_KEY in your .env file."

    budget_query = {
        "budget": "cheap budget hotels under 1500 rupees",
        "mid-range": "best mid-range hotels 2000 to 5000 rupees",
        "luxury": "luxury 5-star hotels",
    }.get(budget.lower(), "best hotels")

    query = f"{budget_query} in {city} with reviews and prices"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "query": query,
        "limit": 5,
        "scrapeOptions": {
            "formats": ["markdown"],
            "onlyMainContent": True
        }
    }

    try:
        resp = requests.post(FIRECRAWL_URL, json=payload, headers=headers, timeout=45)
        data = resp.json()

        if data.get("success") and data.get("data"):
            markdown_chunks = []
            for item in data["data"]:
                if "markdown" in item:
                    source = f"Source: {item.get('url', 'Unknown')}\n"
                    markdown_chunks.append(source + item["markdown"])

            combined_md = "\n\n---\n\n".join(markdown_chunks)
            return f"Hotels near {city} {coord_info}{combined_md[:10000]}"
        else:
            return f"No hotel data found for {city}. Try adjusting the search parameters."

    except Exception as e:
        return f"Hotel search failed: {str(e)}"


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print(research_hotels("vizag", "mid-range"))

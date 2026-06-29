"""
Uses Nominatim (geocoding) + Overpass API (POI lookup)
to find and cluster nearby attractions for day planning.
No API key needed — both are free OpenStreetMap services.
"""
import requests
import time
from geopy.distance import geodesic


OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

HEADERS = {"User-Agent": "TinaTravelBot/1.0 (travel planning assistant)"}


# Step 1: Get coordinates for a city 

def geocode_city(city: str) -> dict:
    """Return lat/lon for a city name using Nominatim."""
    params = {"q": city, "format": "json", "limit": 1}
    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=10)
        data = resp.json()
        if data:
            return {
                "city": city,
                "lat": float(data[0]["lat"]),
                "lon": float(data[0]["lon"]),
                "display_name": data[0]["display_name"],
            }
    except Exception as e:
        return {"error": str(e)}
    return {"error": "City not found"}


# Step 2: Fetch tourist attractions via Overpass

def get_attractions(lat: float, lon: float, radius_km: int = 30) -> list:
    """Query Overpass for tourist attractions around a coordinate.
    Returns a list of places with name, lat, lon, type."""
    radius_m = radius_km * 1000

    # Overpass QL — fetch tourism nodes and ways
    query = f"""
    [out:json][timeout:60];
    (
      node["tourism"~"attraction|museum|viewpoint|artwork|zoo|theme_park"]
          (around:{radius_m},{lat},{lon});
      node["historic"~"monument|castle|ruins|memorial"]
          (around:{radius_m},{lat},{lon});
      node["leisure"~"park|nature_reserve|beach"]
          (around:{radius_m},{lat},{lon});
    );
    out body 80;
    """

    try:
        resp = requests.post(OVERPASS_URL, data={"data": query}, headers=HEADERS, timeout=90)
        if resp.status_code != 200 or not resp.text.strip():
            return [{"error": f"Overpass API error: status={resp.status_code}, body={resp.text[:200]}"}]
        elements = resp.json().get("elements", [])

        places = []
        for el in elements:
            name = el.get("tags", {}).get("name")
            if not name:
                continue
            place_lat = el.get("lat")
            place_lon = el.get("lon")
            if place_lat and place_lon:
                places.append({
                    "name": name,
                    "lat": place_lat,
                    "lon": place_lon,
                    "type": el.get("tags", {}).get("tourism")
                          or el.get("tags", {}).get("historic")
                          or el.get("tags", {}).get("leisure", "attraction"),
                })

        return places

    except Exception as e:
        return [{"error": str(e)}]

# Step 3: Cluster places by proximity into day groups 
def cluster_by_proximity(places: list, num_days: int) -> list[list]:
    """Simple greedy clustering: group nearby places together so each
    day's plan minimises travel distance.
    Returns a list of groups, one per day."""
    if not places:
        return []

    # Deduplicate
    seen = set()
    unique = []
    for p in places:
        if p["name"] not in seen:
            seen.add(p["name"])
            unique.append(p)

    # Greedy nearest-neighbor grouping
    remaining = unique.copy()
    groups = []

    places_per_day = max(1, len(remaining) // num_days)

    for day in range(num_days):
        if not remaining:
            break
        group = [remaining.pop(0)]          # seed with first unvisited place

        while len(group) < places_per_day and remaining:
            last = group[-1]
            # Find closest unvisited place to the last in group
            closest = min(
                remaining,
                key=lambda p: geodesic((last["lat"], last["lon"]), (p["lat"], p["lon"])).km
                        )
            group.append(closest)
            remaining.remove(closest)

        groups.append(group)

    # Spill any leftover places into the last day
    if remaining and groups:
        groups[-1].extend(remaining)

    return groups


# ── Main entry point used by Day Planner agent 
def build_day_clusters(city: str, num_days: int) -> str:
    """
    Full pipeline: geocode → fetch attractions → cluster by day.
    Returns a formatted string ready for the LLM to narrate.
    """
    # 1. Geocode
    geo = geocode_city(city)
    if "error" in geo:
        return f"Could not find location: {city}"

    lat, lon = geo["lat"], geo["lon"]

    # 2. Fetch POIs
    time.sleep(1)   # be polite to Nominatim rate limits
    attractions = get_attractions(lat, lon)

    if not attractions or "error" in attractions[0]:
        return f"Could not fetch attractions for {city}."

    # 3. Cluster
    clusters = cluster_by_proximity(attractions, num_days)

    # 4. Format output
    lines = [f"📍 Location: {geo['display_name']}", ""]
    for i, group in enumerate(clusters, 1):
        lines.append(f"Day {i}:")
        for place in group:
            lines.append(f"  • {place['name']} ({place['type']})")
        lines.append("")

    return "\n".join(lines)

if __name__ == "__main__":
    print(build_day_clusters("vizag", 5))

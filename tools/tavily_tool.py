import os
from tavily import TavilyClient

def tavily_search(query: str, max_results: int = 5) -> str:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or api_key == "your_tavily_api_key_here":
        return "Error: TAVILY_API_KEY is not configured."

    client = TavilyClient(api_key=api_key)

    try:
        response = client.search(query=query, search_depth="advanced", max_results=max_results, include_answer=True)
        parts = []
        # Tavily's top-level answer (fast summary)
        if response.get("answer"):
            parts.append(f"Summary: {response['answer']}")

        # Individual result snippets for detail
        for i, result in enumerate(response.get("results", []), 1):
            title = result.get("title", "")
            content = result.get("content", "")
            url = result.get("url", "")
            parts.append(f"\n[{i}] {title}\n{content}\nSource: {url}")

        return "\n".join(parts) if parts else "No results found."

    except Exception as e:
        return f"Search failed: {str(e)}"

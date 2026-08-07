"""
AYO AI — Web Research Agent
=============================
Searches the web using DuckDuckGo (no API key needed),
scrapes content from top results, and returns AI-summarised output.
"""

import logging
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

log = logging.getLogger("ayo.research")

MAX_RESULTS  = 5
MAX_CHARS    = 3000     # Chars to extract from each page
REQUEST_TIMEOUT = 10


class ResearchAgent:
    def __init__(self, brain=None):
        """brain: LLMBrain instance for summarisation."""
        self.brain = brain
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def search(self, query: str, summarise: bool = True) -> dict:
        """
        Search DuckDuckGo, scrape top pages, optionally summarise.
        Returns: { "query": str, "summary": str, "sources": [...] }
        """
        log.info(f"🔍 Researching: '{query}'")

        results = self._ddg_search(query)
        if not results:
            return {"query": query, "summary": "No results found.", "sources": []}

        # Scrape content from top pages
        contents = []
        sources   = []
        for r in results[:MAX_RESULTS]:
            url   = r.get("href", "")
            title = r.get("title", "")
            body  = r.get("body", "")

            # Use DuckDuckGo snippet first (fast), then scrape if empty
            if body:
                contents.append(f"[{title}] {body}")
            else:
                scraped = self._scrape(url)
                if scraped:
                    contents.append(f"[{title}] {scraped}")

            sources.append({"title": title, "url": url})

        combined = "\n\n".join(contents)[:MAX_CHARS * MAX_RESULTS]

        if summarise and self.brain:
            summary = self.brain.summarise(
                f"Search query: {query}\n\nContent from top results:\n{combined}"
            )
        else:
            summary = combined[:1000] + ("…" if len(combined) > 1000 else "")

        return {
            "query":   query,
            "summary": summary,
            "sources": sources[:5],
        }

    def _ddg_search(self, query: str) -> list[dict]:
        try:
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=MAX_RESULTS))
        except Exception as e:
            log.error(f"DuckDuckGo search error: {e}")
            return []

    def _scrape(self, url: str) -> str:
        """Scrape plain text from a URL."""
        try:
            resp = self._session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            # Remove scripts and styles
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            return text[:MAX_CHARS]
        except Exception as e:
            log.debug(f"Scrape failed ({url}): {e}")
            return ""

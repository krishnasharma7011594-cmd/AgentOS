"""
WebSearchTool

Provides live web search capability to AgentOS agents via the DuckDuckGo
search API (no API key required). The tool is registered in ToolRegistry at
startup and discovered by agents through the registry — agents never import
this module directly.

When DuckDuckGo is unreachable (CI, offline env, rate-limited), the tool
returns a graceful degradation message so the ReAct loop can observe the
failure and decide how to proceed rather than throwing an uncaught exception.

Architecture Layer: Core / Tools / Implementations
"""

from typing import Any, List

from core.logging.logger import logger
from core.tools.base import BaseTool


class WebSearchTool(BaseTool):
    """
    Searches the web using DuckDuckGo and returns a formatted snippet list.

    Registered under the name 'web_search'. The ReAct reasoner selects this
    tool when the LLM determines that current, external information is needed
    to answer the user's question.

    Parameters accepted by execute():
        query (str, required)   : The search query string.
        max_results (int, opt.) : Number of results to return (default: 3).
    """

    # Number of results to return when the caller doesn't specify
    DEFAULT_MAX_RESULTS: int = 3

    # Hard ceiling to prevent enormous prompts blowing the LLM context window
    MAX_ALLOWED_RESULTS: int = 8

    def __init__(self) -> None:
        super().__init__(
            name="web_search",
            description=(
                "Search the web for current information about a topic. "
                "Use this when you need facts, news, or data you might not have."
            ),
            parameters={
                "query": {
                    "type": "string",
                    "description": "The search query to send to DuckDuckGo.",
                    "required": True,
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 3, max: 8).",
                    "required": False,
                },
            },
        )

    async def execute(
        self,
        query: str,
        max_results: int = DEFAULT_MAX_RESULTS,
        **kwargs: Any,
    ) -> str:
        """
        Perform a DuckDuckGo text search and return a formatted result string.

        The returned string is injected directly into the ReAct observation
        prompt, so it's plain text — not JSON — to minimise token overhead.

        Args:
            query:       Search query string.
            max_results: How many results to include (capped at MAX_ALLOWED_RESULTS).

        Returns:
            Multi-line string of search results, or an error description.
        """
        # Clamp to the hard ceiling regardless of caller input
        max_results = min(max_results, self.MAX_ALLOWED_RESULTS)

        logger.info("web_search_start", query=query, max_results=max_results)

        try:
            # Import lazily so environments without the package can still boot;
            # the tool will just return an error string rather than crashing startup.
            from duckduckgo_search import DDGS  # type: ignore[import-untyped]

            raw_results: List[Any] = []
            # DDGS is synchronous; we keep I/O minimal to avoid blocking the loop
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))

            if not raw_results:
                logger.warning("web_search_empty", query=query)
                return f"No results found for query: '{query}'"

            # Format: title, URL, and a short body snippet per result
            formatted = _format_results(raw_results)
            logger.info("web_search_success", query=query, result_count=len(raw_results))
            return formatted

        except ImportError:
            # duckduckgo-search is not installed — can happen in minimal CI envs
            error_msg = (
                "WebSearchTool is unavailable: 'duckduckgo-search' package not installed. "
                "Install it with: pip install duckduckgo-search"
            )
            logger.error("web_search_import_error", detail=error_msg)
            return error_msg

        except Exception as exc:
            # Network errors, rate limits, DNS failures — return gracefully
            error_msg = f"Web search failed for query '{query}': {exc}"
            logger.error("web_search_error", query=query, error=str(exc))
            return error_msg


def _format_results(results: List[Any]) -> str:
    """
    Convert DuckDuckGo result dicts into a compact, prompt-friendly string.

    Each result dict has keys: 'title', 'href', 'body'.
    We format them as numbered entries so the LLM can easily reference them.
    """
    lines = []
    for i, r in enumerate(results, start=1):
        title = r.get("title", "No title")
        href = r.get("href", "")
        body = r.get("body", "No description available.")
        lines.append(f"[{i}] {title}")
        lines.append(f"    URL: {href}")
        lines.append(f"    {body}")
        lines.append("")  # blank line between results
    return "\n".join(lines).strip()

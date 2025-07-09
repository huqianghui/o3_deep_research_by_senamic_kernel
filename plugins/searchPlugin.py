"""
Search plugin for Tavily API integration.
"""
import datetime as dt
import json
import logging
from typing import Any, Dict, List, Optional

from semantic_kernel.functions import kernel_function
from tavily import TavilyClient
import os
from utils.util import truncate_text, validate_search_results

logger = logging.getLogger(__name__)


class SearchPlugin:
    """Plugin for performing web searches using Tavily API."""

    def __init__(self):
        """Initialize the search plugin."""
        self.client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        logger.info("SearchPlugin initialized")

    @kernel_function(
        name="tavily_search",
        description="Perform comprehensive web search using Tavily API with advanced filtering and image support"
    )
    def tavily_search(
        self,
        query: str,
        top_k: int = None,
        time_range: Optional[str] = None,
        topic: str = "general",
        search_depth: str = "basic",
        include_image_descriptions: bool = False
    ) -> str:
        """
        Perform web search using Tavily API with enhanced error handling.

        Args:
            query: Search query string
            top_k: Maximum number of results to return (default from config)
            time_range: Optional time filter ("day", "week", "month", "year")
            topic: Search topic ("general", "news", "finance")
            search_depth: Search depth ("basic", "advanced")
            include_image_descriptions: Include query-related images and descriptions

        Returns:
            str: JSON string containing search results
        """
        if top_k is None:
            top_k = int(os.getenv("DEFAULT_MAX_RESULTS","5"))
        logger.info(
            f"Performing Tavily search - Query: '{truncate_text(query, 50)}', "
            f"Results: {top_k}, Time: {time_range}, Topic: {topic}, "
            f"Depth: {search_depth}, Images: {include_image_descriptions}"
        )

        try:
            # Build search parameters
            search_params = self._build_search_params(
                query, top_k, time_range, topic, search_depth, include_image_descriptions
            )
            # Execute search with retry logic
            response = self._execute_search_with_retry(search_params)

            # Process and validate response
            results = self._process_search_response(response, include_image_descriptions)

            logger.info(f"Search completed successfully. Found {len(results)} results")
            return json.dumps(results, ensure_ascii=False, indent=2)

        except Exception as e:
            error_msg = f"Tavily search failed: {str(e)}"
            logger.error(error_msg)
            return json.dumps([{"error": error_msg}], ensure_ascii=False)

    def _build_search_params(
        self,
        query: str,
        top_k: int,
        time_range: Optional[str],
        topic: str,
        search_depth: str,
        include_image_descriptions: bool
    ) -> Dict[str, Any]:
        """Build search parameters dictionary."""
        search_params = {
            "query": query,
            "max_results": min(top_k, 50),  # Limit to reasonable maximum
            "topic": topic,
            "search_depth": search_depth,
            "include_answer": False,
            "include_raw_content": False
        }
        if include_image_descriptions and include_image_descriptions is True:
            search_params["include_image_descriptions"] = True
            search_params["include_images"] = True
        # Add time_range only if specified and valid
        valid_time_ranges = ["day", "week", "month", "year"]
        if time_range and time_range in valid_time_ranges:
            search_params["time_range"] = time_range
        return search_params

    def _execute_search_with_retry(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute search with retry logic."""
        last_exception = None

        for attempt in range(int(os.getenv("MAX_RETRIES", 3))):
            try:
                response = self.client.search(**search_params)

                # Handle string response
                if isinstance(response, str):
                    try:
                        response = json.loads(response)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Invalid JSON response from Tavily API: {e}")

                if not isinstance(response, dict):
                    raise ValueError(f"Unexpected response type: {type(response)}")

                return response

            except Exception as e:
                last_exception = e
                logger.warning(f"Search attempt {attempt + 1} failed: {e}")

                if attempt < int(os.getenv("MAX_RETRIES", 3)) - 1:
                    # Exponential backoff
                    import time
                    time.sleep(2 ** attempt)

        raise last_exception

    def _process_search_response(
        self,
        response: Dict[str, Any],
        include_image_descriptions: bool
    ) -> List[Dict[str, Any]]:
        """Process and structure search response."""
        results = []
        search_results = response.get('results', [])
        if search_results is None:
            search_results = []
        for result in search_results:
            if not isinstance(result, dict):
                continue

            result_data = {
                "url": result.get('url', ''),
                "title": result.get('title', ''),
                "snippet": result.get('content', ''),
                "score": result.get('score', 0.0),
                "crawled_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "published_date": result.get('published_date', ''),
                "domain": self._extract_domain(result.get('url', ''))
            }
            # Add additional metadata if available
            if 'raw_content' in result and result['raw_content'] is not None:
                result_data['raw_content'] = truncate_text(result['raw_content'], 500)

            results.append(result_data)

        # Process images if requested
        if include_image_descriptions:
            self._process_image_results(response, results)

        # Validate results structure
        if not validate_search_results(results):
            logger.warning("Search results failed validation")
            return []

        return results

    def _process_image_results(self, response: Dict[str, Any], results: List[Dict[str, Any]]) -> None:
        """Process and attach image results."""
        image_results = response.get('images', [])

        if not image_results or not results:
            return

        image_data = []
        for image_result in image_results:
            if isinstance(image_result, dict):
                url = image_result.get('url', '')
                description = image_result.get('description', '')
                if url and description:
                    image_data.append({
                        "url": url,
                        "description": description,
                        "markdown": f"![{description}]({url})"
                    })

        if image_data:
            # Add images as a separate field
            results[0]["images"] = image_data
            logger.info(f"Added {len(image_data)} images to search results")

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ""

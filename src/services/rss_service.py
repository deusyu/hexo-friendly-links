"""Service for parsing RSS feeds."""

import feedparser
import requests
from copy import deepcopy
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class RSSService:
    """Service for parsing RSS feeds."""
    
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def _fallback(self, rss_url: str, previous_items, max_items: int):
        if previous_items:
            logger.warning("Retaining %s last valid RSS items for %s after a fetch/parse failure",
                           min(len(previous_items), max_items), rss_url)
        return deepcopy((previous_items or [])[:max_items])

    def get_feed_content(self, rss_url: str, max_items: int = 10,
                         previous_items: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Parse RSS feed and return recent entries.
        
        Args:
            rss_url: URL of the RSS feed
            max_items: Maximum number of items to return
            previous_items: Last valid published entries to retain on failure
            
        Returns:
            List of feed entries with cleaned data
        """
        if not rss_url or not rss_url.strip():
            logger.debug("Empty RSS URL provided")
            return []
        
        try:
            logger.debug(f"Parsing RSS feed: {rss_url}")
            
            with requests.get(
                rss_url.strip(), headers={"User-Agent": self.USER_AGENT},
                timeout=self.timeout, allow_redirects=True
            ) as response:
                content_type = response.headers.get("Content-Type", "unknown")
                if not 200 <= response.status_code < 300:
                    logger.warning("RSS fetch failed for %s: HTTP %s; content-type=%s; final-url=%s",
                                   rss_url, response.status_code, content_type, response.url)
                    return self._fallback(rss_url, previous_items, max_items)
                feed = feedparser.parse(response.content)

            if feed.bozo:
                error = feed.get("bozo_exception")
                logger.warning("RSS parse failed for %s: %s: %s; content-type=%s",
                               rss_url, type(error).__name__, error, content_type)
                return self._fallback(rss_url, previous_items, max_items)
            if not feed.get("version"):
                logger.warning("RSS parse failed for %s: no RSS/Atom document; content-type=%s",
                               rss_url, content_type)
                return self._fallback(rss_url, previous_items, max_items)
            
            items = []
            for entry in feed.entries:
                item = {
                    "title": getattr(entry, "title", ""),
                    "link": getattr(entry, "link", ""),
                    "published": getattr(entry, "published", None),
                    "published_parsed": getattr(entry, "published_parsed", None),
                    "author": getattr(entry, "author", None),
                    "summary": getattr(entry, "summary", None),
                }
                items.append(item)
            
            # Sort by published date (newest first)
            # Filter out items with None published_parsed first
            items_with_date = [item for item in items if item["published_parsed"]]
            items_without_date = [item for item in items if not item["published_parsed"]]
            
            items_with_date = sorted(items_with_date, key=lambda x: x["published_parsed"], reverse=True)
            items = items_with_date + items_without_date
            
            # Limit the number of items
            if len(items) > max_items:
                items = items[:max_items]
            
            logger.debug(f"Successfully parsed {len(items)} items from RSS feed")
            return items
            
        except Exception as e:
            logger.warning("RSS fetch/parse failed for %s: %s: %s",
                           rss_url, type(e).__name__, e)
            return self._fallback(rss_url, previous_items, max_items)

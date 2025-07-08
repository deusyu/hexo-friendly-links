"""Service for parsing RSS feeds."""

import feedparser
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class RSSService:
    """Service for parsing RSS feeds."""
    
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    
    def get_feed_content(self, rss_url: str, max_items: int = 10) -> List[Dict[str, Any]]:
        """
        Parse RSS feed and return recent entries.
        
        Args:
            rss_url: URL of the RSS feed
            max_items: Maximum number of items to return
            
        Returns:
            List of feed entries with cleaned data
        """
        if not rss_url or not rss_url.strip():
            logger.debug("Empty RSS URL provided")
            return []
        
        try:
            logger.debug(f"Parsing RSS feed: {rss_url}")
            
            feed = feedparser.parse(
                rss_url.strip(),
                agent=self.USER_AGENT
            )
            
            if feed.bozo:
                logger.warning(f"RSS feed has parsing issues: {rss_url}")
            
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
            items = sorted(
                items,
                key=lambda x: x["published_parsed"] or (1970, 1, 1, 0, 0, 0, 0, 0, 0),
                reverse=True
            )
            
            # Limit the number of items
            if len(items) > max_items:
                items = items[:max_items]
            
            logger.debug(f"Successfully parsed {len(items)} items from RSS feed")
            return items
            
        except Exception as e:
            logger.warning(f"Failed to parse RSS feed {rss_url}: {e}")
            return [] 
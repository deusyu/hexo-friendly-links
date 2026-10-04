"""Service for checking link availability."""

import requests
from typing import Literal
import logging

logger = logging.getLogger(__name__)

LinkStatus = Literal["active", "404", "error"]


class LinkChecker:
    """Service for checking if links are accessible."""
    
    def __init__(self, timeout: int = 5):
        """
        Initialize link checker.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
    
    def check_link(self, url: str) -> LinkStatus:
        """
        Check if a link is accessible.
        
        Args:
            url: URL to check
            
        Returns:
            Status of the link: "active", "404", or "error"
        """
        if not url or not url.strip():
            return "404"
        
        try:
            response = requests.head(
                url.strip(),
                timeout=self.timeout,
                allow_redirects=True
            )
            
            status_code = response.status_code
            response.close()
            # Some servers reject HEAD even though their pages support GET.
            if status_code in (403, 405, 501):
                with requests.get(
                    url.strip(), timeout=self.timeout,
                    allow_redirects=True, stream=True
                ) as response:
                    status_code = response.status_code

            logger.debug("Link %s returned status %s", url, status_code)
            return "active" if 200 <= status_code < 300 else "404"
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout checking link: {url}")
            return "error"
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error checking link: {url}")
            return "404"
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error checking link {url}: {e}")
            return "error"
        except Exception as e:
            logger.error(f"Unexpected error checking link {url}: {e}")
            return "error"

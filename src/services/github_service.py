"""GitHub API service for fetching issues and labels."""

import requests
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class GitHubService:
    """Service for interacting with GitHub API."""
    
    BASE_URL = "https://api.github.com"
    HEADERS = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "hexo-friendly-links/2.2 (Python requests)",
    }
    
    def __init__(self, timeout: int = 10):
        """
        Initialize GitHub service.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
    
    def get_labels(self, repo: str) -> List[Dict[str, Any]]:
        """
        Get labels from a repository.
        
        Args:
            repo: Repository in format 'owner/repo'
            
        Returns:
            List of label data
            
        Raises:
            requests.RequestException: If API request fails
        """
        url = f"{self.BASE_URL}/repos/{repo}/labels"
        
        try:
            response = requests.get(
                url,
                headers=self.HEADERS,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            labels = response.json()
            logger.info(f"Retrieved {len(labels)} labels from {repo}")
            return labels
            
        except requests.RequestException as e:
            logger.error(f"Failed to get labels from {repo}: {e}")
            raise
    
    def get_issues(
        self,
        repo: str,
        labels: Optional[List[str]] = None,
        state: str = "all",
        sort: str = "created"
    ) -> List[Dict[str, Any]]:
        """
        Get issues from a repository with pagination support.
        
        Args:
            repo: Repository in format 'owner/repo'
            labels: List of labels to filter by
            state: Issue state (all, open, closed)
            sort: Sort order
            
        Returns:
            List of issue data
            
        Raises:
            requests.RequestException: If API request fails
        """
        all_issues = []
        page = 1
        per_page = 100
        
        while True:
            issues = self._get_issues_page(
                repo=repo,
                labels=labels or [],
                state=state,
                sort=sort,
                page=page,
                per_page=per_page
            )
            
            all_issues.extend(issues)
            
            # If we got fewer issues than per_page, we've reached the end
            if len(issues) < per_page:
                break
                
            page += 1
        
        logger.info(f"Retrieved {len(all_issues)} issues from {repo}")
        return all_issues
    
    def _get_issues_page(
        self,
        repo: str,
        labels: List[str],
        state: str,
        sort: str,
        page: int,
        per_page: int
    ) -> List[Dict[str, Any]]:
        """Get a single page of issues."""
        url = f"{self.BASE_URL}/repos/{repo}/issues"
        
        params = {
            "state": state,
            "per_page": per_page,
            "page": page,
            "sort": sort,
        }
        
        if labels:
            params["labels"] = ",".join(labels)
        
        try:
            response = requests.get(
                url,
                params=params,
                headers=self.HEADERS,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            issues = response.json()
            logger.debug(f"Retrieved page {page} with {len(issues)} issues")
            return issues
            
        except requests.RequestException as e:
            logger.error(f"Failed to get issues page {page} from {repo}: {e}")
            raise 
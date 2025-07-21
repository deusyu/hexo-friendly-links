"""
Main entry point for Hexo Friendly Links Generator.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List

from .utils import setup_logger, load_config
from .services import GitHubService, LinkChecker, RSSService
from .parsers import JsonParser, TableParser

# Version from package
from . import __version__

# Setup logging
logger = setup_logger(__name__)


class FriendlyLinksGenerator:
    """Main generator class for processing friendly links."""
    
    def __init__(self, config_path: str = "config.yml"):
        """
        Initialize the generator.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.github_service = GitHubService()
        self.link_checker = LinkChecker()
        self.rss_service = RSSService()
        
        # Initialize parsers
        self.parsers = [JsonParser, TableParser]
    
    def parse_issue(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse an issue using appropriate parser.
        
        Args:
            issue_data: GitHub issue data
            
        Returns:
            Parsed friendly link data
        """
        body = issue_data.get("body", "")
        
        # Try each parser until one works
        for parser_class in self.parsers:
            if parser_class.can_parse(body):
                result = parser_class.parse(issue_data)
                if result:
                    return result
        
        # If no parser worked, log warning and return basic structure
        logger.warning(f"Could not parse issue #{issue_data.get('number')}")
        return {"raw": issue_data}
    
    def process_issues(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Process all issues and generate grouped results.
        
        Returns:
            Dictionary with grouped friendly links data
        """
        logger.info("Starting to process issues...")
        
        # Get all issues from repository
        all_issues = self.github_service.get_issues(
            repo=self.config.issues.repo,
            state="all",
            sort=self.config.issues.sort
        )
        
        # Parse all issues
        parsed_issues = []
        for issue in all_issues:
            parsed_issue = self.parse_issue(issue)
            parsed_issues.append(parsed_issue)
        
        # Check link status and get RSS content for all parsed issues
        for issue in parsed_issues:
            # Check link status if URL exists (matching original logic)
            if "url" in issue and issue["url"]:
                try:
                    # Use requests.head directly like original code for consistency
                    import requests
                    requests.head(issue["url"], timeout=5)
                    issue["status"] = "active"
                except:
                    issue["status"] = "404"
            
            # Get RSS content if feed URL exists  
            if "url-feed" in issue and issue["url-feed"]:
                issue["rss"] = self.rss_service.get_feed_content(issue["url-feed"])
        
        logger.info(f"Processed {len(parsed_issues)} issues")
        
        # Generate output groups
        output = {"all": parsed_issues}
        
        # Process configured groups
        for group_config in self.config.issues.groups:
            filtered_issues = self._filter_issues_for_group(parsed_issues, group_config)
            output[group_config.name] = filtered_issues
            logger.info(f"Group '{group_config.name}': {len(filtered_issues)} issues")
        
        # Remove raw data if configured (after all grouping is done)
        if not self.config.issues.keep_raw:
            self._remove_raw_data(parsed_issues)
        
        return output
    
    def _filter_issues_for_group(self, issues: List[Dict[str, Any]], group_config) -> List[Dict[str, Any]]:
        """Filter issues based on group configuration."""
        filtered = issues
        
        # Filter by state
        if group_config.state != "all":
            filtered = [
                issue for issue in filtered
                if issue.get("raw", {}).get("state") == group_config.state
            ]
        
        # Filter by labels
        if group_config.labels:
            required_labels = set(group_config.labels)
            filtered = [
                issue for issue in filtered
                if required_labels.issubset(
                    set(label["name"] for label in issue.get("raw", {}).get("labels", []))
                )
            ]
        
        return filtered
    
    def _remove_raw_data(self, issues: List[Dict[str, Any]]) -> None:
        """Remove raw GitHub data from all issues."""
        for issue in issues:
            issue.pop("raw", None)
    
    def save_results(self, output: Dict[str, List[Dict[str, Any]]], output_dir: str = "json") -> None:
        """
        Save results to JSON files.
        
        Args:
            output: Generated friendly links data
            output_dir: Output directory
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        for group_name, issues in output.items():
            file_path = output_path / f"{group_name}.json"
            
            # Create output structure with metadata
            file_content = {
                "version": __version__,
                "config": self.config.model_dump(),
                "label": group_name,
                "content": issues,
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(file_content, file, ensure_ascii=False, indent=4)
            
            logger.info(f"Generated file: {file_path}")
        
        logger.info("All files generated successfully")


def main() -> None:
    """Main entry point."""
    try:
        generator = FriendlyLinksGenerator()
        output = generator.process_issues()
        generator.save_results(output)
        
        logger.info("Friendly links generation completed successfully")
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise


if __name__ == "__main__":
    main() 
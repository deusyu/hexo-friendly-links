"""Parser for table format in issue body."""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TableParser:
    """Parser for extracting table data from issue body."""
    
    # Mapping from Chinese field names to English keys
    FIELD_MAPPING = {
        "title": "博客名称",
        "url": "博客地址", 
        "avatar": "博客图标",
        "description": "博客描述",
        "url-friends": "友链地址",
        "url-feed": "订阅地址",
    }
    
    @staticmethod
    def can_parse(body: str) -> bool:
        """Check if the body contains table format (has ### sections)."""
        return "###" in body
    
    @staticmethod
    def parse(issue_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse table format from issue body.
        
        Args:
            issue_data: GitHub issue data
            
        Returns:
            Parsed friendly link data or None if parsing fails
        """
        try:
            body = issue_data.get("body", "").strip()
            
            # Split by ### to get sections
            sections = body.split("###")
            raw_data = {}
            
            for section in sections:
                if not section.strip():
                    continue
                    
                # Replace Windows line endings
                section = section.replace("\r\n", "\n")
                
                # Split by double newline to separate title and value
                parts = section.split("\n\n")
                if len(parts) < 2:
                    continue
                    
                key = parts[0].strip()
                value = parts[1].strip()
                raw_data[key] = value
            
            # Map Chinese field names to English keys
            result = {}
            for eng_key, chi_key in TableParser.FIELD_MAPPING.items():
                value = raw_data.get(chi_key, "").strip()
                # Handle GitHub's "_No response_" placeholder
                result[eng_key] = "" if value == "_No response_" else value
            
            # Add the raw issue data
            result = dict(result, **{"raw": issue_data})
            
            logger.debug(f"Successfully parsed table from issue #{issue_data.get('number')}")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing table from issue #{issue_data.get('number')}: {e}")
            return None 
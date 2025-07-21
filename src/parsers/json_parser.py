"""Parser for JSON format in issue body."""

import json
import re
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class JsonParser:
    """Parser for extracting JSON data from issue body."""
    
    @staticmethod
    def can_parse(body: str) -> bool:
        """Check if the body contains JSON format."""
        return bool(re.findall(r"```json([\s\S]+?)```", body))
    
    @staticmethod
    def parse(issue_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse JSON format from issue body.
        
        Args:
            issue_data: GitHub issue data
            
        Returns:
            Parsed friendly link data or None if parsing fails
        """
        try:
            body = issue_data.get("body", "")
            json_matches = re.findall(r"```json([\s\S]+?)```", body)
            
            if not json_matches:
                logger.warning(f"No JSON block found in issue #{issue_data.get('number')}")
                return None
            
            # Parse the first JSON block found
            json_str = json_matches[0].strip()
            if not json_str:
                logger.warning(f"Empty JSON block in issue #{issue_data.get('number')}")
                return None
                
            json_data = json.loads(json_str)
            
            # Add the raw issue data
            result = dict(json_data, **{"raw": issue_data})
            
            logger.debug(f"Successfully parsed JSON from issue #{issue_data.get('number')}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in issue #{issue_data.get('number')}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing JSON from issue #{issue_data.get('number')}: {e}")
            return None 
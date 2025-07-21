"""
Avatar optimization service for better frontend loading experience.
"""

import requests
from typing import Dict, Any, Optional
import logging
from urllib.parse import urlparse
import base64
import io

logger = logging.getLogger(__name__)


class AvatarOptimizer:
    """Service for optimizing avatar loading experience."""
    
    def __init__(self, timeout: int = 5):
        """
        Initialize avatar optimizer.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.default_avatars = [
            "https://ui-avatars.com/api/?name={name}&background=6366f1&color=fff&size=128",
            "https://api.dicebear.com/7.x/avataaars/svg?seed={name}",
            "https://gravatar.com/avatar/00000000000000000000000000000000?d=retro&s=128"
        ]
    
    def optimize_avatar(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize avatar data for better frontend loading.
        
        Args:
            issue_data: Friend link data
            
        Returns:
            Optimized data with avatar loading information
        """
        original_avatar = issue_data.get("avatar", "")
        title = issue_data.get("title", "User")
        
        # Test original avatar
        avatar_status = self._test_avatar_url(original_avatar)
        
        # Generate fallback avatars
        fallback_avatars = self._generate_fallback_avatars(title)
        
        # Add optimization data
        issue_data.update({
            "avatar_status": avatar_status["status"],
            "avatar_load_time": avatar_status.get("load_time", 0),
            "avatar_fallbacks": fallback_avatars,
            "avatar_optimized": True
        })
        
        # If original avatar failed, use first fallback as primary
        if avatar_status["status"] != "success" and fallback_avatars:
            issue_data["avatar"] = fallback_avatars[0]
            logger.info(f"Using fallback avatar for {title}: {fallback_avatars[0]}")
        
        return issue_data
    
    def _test_avatar_url(self, url: str) -> Dict[str, Any]:
        """Test avatar URL accessibility and performance."""
        if not url or not url.strip():
            return {"status": "empty", "error": "Empty URL"}
        
        try:
            import time
            start_time = time.time()
            
            response = requests.head(
                url.strip(),
                timeout=self.timeout,
                allow_redirects=True,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            
            load_time = time.time() - start_time
            
            if response.status_code == 200:
                # Check if it's actually an image
                content_type = response.headers.get('content-type', '').lower()
                if any(img_type in content_type for img_type in ['image/', 'application/octet-stream']):
                    return {
                        "status": "success",
                        "load_time": round(load_time * 1000),  # Convert to milliseconds
                        "content_type": content_type,
                        "size": response.headers.get('content-length', 'unknown')
                    }
                else:
                    return {"status": "not_image", "content_type": content_type}
            else:
                return {"status": "http_error", "code": response.status_code}
                
        except requests.exceptions.Timeout:
            return {"status": "timeout", "error": "Request timeout"}
        except requests.exceptions.ConnectionError:
            return {"status": "connection_error", "error": "Connection failed"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _generate_fallback_avatars(self, title: str) -> list:
        """Generate fallback avatar URLs."""
        # Clean title for URL use
        clean_name = "".join(c for c in title if c.isalnum() or c in " -_")[:20]
        
        fallbacks = []
        for template in self.default_avatars:
            try:
                fallback_url = template.format(name=clean_name.replace(" ", "+"))
                fallbacks.append(fallback_url)
            except:
                continue
        
        return fallbacks
    
    def generate_loading_placeholder(self, title: str) -> str:
        """Generate a data URL for loading placeholder."""
        # Create simple SVG placeholder
        svg_content = f"""
        <svg width="64" height="64" xmlns="http://www.w3.org/2000/svg">
            <rect width="64" height="64" fill="#f3f4f6"/>
            <circle cx="32" cy="24" r="8" fill="#d1d5db"/>
            <path d="M20 40 Q20 36 24 36 L40 36 Q44 36 44 40 L44 48 L20 48 Z" fill="#d1d5db"/>
            <text x="32" y="58" text-anchor="middle" font-size="8" fill="#6b7280">
                {title[:1].upper()}
            </text>
        </svg>
        """
        
        # Convert to data URL
        svg_bytes = svg_content.encode('utf-8')
        b64_svg = base64.b64encode(svg_bytes).decode('utf-8')
        return f"data:image/svg+xml;base64,{b64_svg}" 
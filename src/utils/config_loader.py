"""Configuration loading utilities."""

import yaml
from pathlib import Path
from typing import Union
import logging

from ..models import Config

logger = logging.getLogger(__name__)


def load_config(config_path: Union[str, Path] = "config.yml") -> Config:
    """
    Load and validate configuration from YAML file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Validated configuration object
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config validation fails
        yaml.YAMLError: If YAML parsing fails
    """
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            yaml_data = yaml.safe_load(file)
        
        logger.info(f"Loaded configuration from {config_path}")
        
        # Validate using pydantic model
        config = Config(**yaml_data)
        
        logger.info("Configuration validation successful")
        return config
        
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error: {e}")
        raise
    except Exception as e:
        logger.error(f"Configuration validation error: {e}")
        raise ValueError(f"Invalid configuration: {e}") 
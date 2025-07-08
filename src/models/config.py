"""Configuration data models with validation."""

from typing import List, Optional
from pydantic import BaseModel, field_validator


class GroupConfig(BaseModel):
    """Configuration for a friendly links group."""
    
    name: str
    state: str = "all"
    labels: List[str] = []
    
    @field_validator('state')
    @classmethod
    def validate_state(cls, v: str) -> str:
        valid_states = {"all", "open", "closed"}
        if v not in valid_states:
            raise ValueError(f"State must be one of {valid_states}")
        return v


class IssuesConfig(BaseModel):
    """Configuration for GitHub Issues processing."""
    
    repo: str
    groups: List[GroupConfig] = []
    sort: str = "created"
    keep_raw: bool = False
    
    @field_validator('repo')
    @classmethod
    def validate_repo(cls, v: str) -> str:
        if '/' not in v or len(v.split('/')) != 2:
            raise ValueError("Repository must be in format 'owner/repo'")
        return v
    
    @field_validator('sort')
    @classmethod
    def validate_sort(cls, v: str) -> str:
        valid_sorts = {"created", "updated", "comments", "created-desc", "updated-desc", "comments-desc"}
        if v not in valid_sorts:
            raise ValueError(f"Sort must be one of {valid_sorts}")
        return v


class Config(BaseModel):
    """Main configuration model."""
    
    issues: IssuesConfig 
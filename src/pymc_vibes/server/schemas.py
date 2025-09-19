"""Pydantic models for API data validation."""

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field


class Event(BaseModel):
    """A generic event model."""

    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = {}


class ABTestEvent(Event):
    """An event specific to an A/B test."""

    treatment: str  # e.g., 'A', 'B', 'control'
    conversion: bool  # e.g., True for click, False for no click

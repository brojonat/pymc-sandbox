from typing import List

from pydantic import BaseModel


class Trial(BaseModel):
    """A single trial in an experiment."""

    session_id: str
    user_id: str
    variant: str
    timestamp: str
    outcome: bool
    reward: float


class Trials(BaseModel):
    """A collection of trials."""

    trials: list[Trial]


class PosteriorCurve(BaseModel):
    """Represents a posterior curve for plotting."""

    x: List[float]
    y: List[float]


class PosteriorSummary(BaseModel):
    """A complete summary of a posterior distribution."""

    stats: dict
    curve: PosteriorCurve


class ABTestPosteriorSummary(BaseModel):
    """A summary of the posterior distributions for an A/B test."""

    variants: dict[str, PosteriorSummary]

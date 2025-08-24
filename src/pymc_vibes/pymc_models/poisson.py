"""PyMC models for Poisson processes."""

from datetime import datetime
from typing import Optional, Union

import arviz as az
import pandas as pd
import pymc as pm


def fit_poisson_rate(
    event_timestamps: pd.Series,
    ts_start: datetime,
    ts_end: datetime,
    unit: str = "day",
) -> az.InferenceData:
    """
    Fit a Bayesian Poisson model to estimate the event rate.

    Parameters
    ----------
    event_timestamps : pd.Series
        A series of timestamps for each observed event.
    ts_start : datetime
        The start of the observation period.
    ts_end : datetime
        The end of the observation period.
    unit : str, optional
        The time unit for the rate (e.g., "second", "hour", "day"), by default "day".

    Returns
    -------
    az.InferenceData
        The ArviZ InferenceData object containing the posterior samples.
    """
    duration_seconds = (ts_end - ts_start).total_seconds()
    n_events = len(event_timestamps)

    # Normalize duration to the desired unit
    if unit == "day":
        duration_in_unit = duration_seconds / (24 * 60 * 60)
    elif unit == "hour":
        duration_in_unit = duration_seconds / (60 * 60)
    elif unit == "minute":
        duration_in_unit = duration_seconds / 60
    elif unit == "second":
        duration_in_unit = duration_seconds
    else:
        raise ValueError("Unsupported time unit. Use 'second', 'minute', 'hour', or 'day'.")

    with pm.Model() as model:
        # Prior for the rate (lambda)
        rate = pm.Exponential("rate", lam=1.0)

        # Likelihood of the observed number of events
        pm.Poisson("n_events", mu=rate * duration_in_unit, observed=n_events)

        # Sample from the posterior
        idata = pm.sample()

    return idata


def _sample_poisson_interval(
    rate: float,
    start: Union[datetime, float],
    end: Union[datetime, float],
    random_seed: Optional[int] = None,
) -> list[float]:
    """
    Sample event timestamps from a homogeneous Poisson process in a single interval.

    Parameters
    ----------
    rate : float
        The average number of events per second.
    start : Union[datetime, float]
        The start of the time interval (as datetime or Unix timestamp).
    end : Union[datetime, float]
        The end of the time interval (as datetime or Unix timestamp).
    random_seed : Optional[int], optional
        A seed for the random number generator for reproducibility.

    Returns
    -------
    list[float]
        A list of generated timestamps as Unix timestamps (floats).
    """
    start_unix = start.timestamp() if isinstance(start, datetime) else start
    end_unix = end.timestamp() if isinstance(end, datetime) else end
    duration = end_unix - start_unix
    if duration <= 0:
        return []

    expected_events = rate * duration

    with pm.Model():
        n_events = pm.Poisson("n_events", mu=expected_events)
        n_events_sample = (
            pm.sample_prior_predictive(samples=1, random_seed=random_seed)
            .prior["n_events"]
            .values.item()
        )

        if n_events_sample > 0:
            pm.Uniform("timestamps", lower=start_unix, upper=end_unix, size=n_events_sample)
            second_seed = random_seed + 1 if random_seed is not None else None
            prior_pred = pm.sample_prior_predictive(samples=1, random_seed=second_seed)
            return prior_pred.prior["timestamps"].values.flatten().tolist()
        else:
            return []


def generate_poisson_events(
    ts_start: datetime,
    ts_end: datetime,
    rate: float,
    unit: str = "day",
    random_seed: Optional[int] = None,
) -> list[float]:
    """
    Generate timestamps for a homogeneous Poisson process over a given interval.

    This function serves as a wrapper that could be extended to handle
    time-varying rates by calling the underlying sampler for discrete time bins.

    Parameters
    ----------
    ts_start : datetime
        The start of the time interval.
    ts_end : datetime
        The end of the time interval.
    rate : float
        The average number of events per `unit` of time (lambda).
    unit : str, optional
        The time unit for the rate (e.g., "second", "hour", "day"), by default "day".

    Returns
    -------
    list[float]
        A list of generated timestamps as Unix timestamps (floats).
    """
    # Normalize rate to be per second for the helper function
    if unit == "day":
        rate_per_second = rate / (24 * 60 * 60)
    elif unit == "hour":
        rate_per_second = rate / (60 * 60)
    elif unit == "minute":
        rate_per_second = rate / 60
    elif unit == "second":
        rate_per_second = rate
    else:
        raise ValueError("Unsupported time unit. Use 'second', 'minute', 'hour', or 'day'.")

    # For the homogeneous case, we call the sampler once over the whole interval
    return _sample_poisson_interval(
        rate=rate_per_second, start=ts_start, end=ts_end, random_seed=random_seed
    )

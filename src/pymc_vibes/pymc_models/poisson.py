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
    population: int = 1,
    exposure: Optional[float] = None,
    unit: str = "day",
) -> az.InferenceData:
    """
    Fit a Bayesian Poisson model to estimate the event rate per vehicle.

    Parameters
    ----------
    event_timestamps : pd.Series
        A series of timestamps for each observed event.
    ts_start : datetime
        The start of the observation period.
    ts_end : datetime
        The end of the observation period.
    population : int, optional
        The total number of vehicles in the cohort.
    exposure : float, optional
        The total exposure, defined as `population * duration_in_unit`.
        If provided, `population` and `duration` are ignored for exposure calculation.
    unit : str, optional
        The time unit for the rate (e.g., "second", "hour", "day"), by default "day".

    Returns
    -------
    az.InferenceData
        The ArviZ InferenceData object containing the posterior samples for the
        per-vehicle rate.
    """
    n_events = len(event_timestamps)

    if exposure is None:
        duration_seconds = (ts_end - ts_start).total_seconds()

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
            raise ValueError(
                "Unsupported time unit. Use 'second', 'minute', 'hour', or 'day'."
            )
        total_exposure = population * duration_in_unit
    else:
        total_exposure = exposure

    with pm.Model() as model:
        # Prior for the per-vehicle rate (lambda)
        rate = pm.Exponential("rate", lam=1.0)

        # Likelihood of the observed number of events
        pm.Poisson("n_events", mu=rate * total_exposure, observed=n_events)

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
            pm.Uniform(
                "timestamps", lower=start_unix, upper=end_unix, size=n_events_sample
            )
            second_seed = random_seed + 1 if random_seed is not None else None
            prior_pred = pm.sample_prior_predictive(samples=1, random_seed=second_seed)
            return prior_pred.prior["timestamps"].values.flatten().tolist()
        else:
            return []


def generate_poisson_events(
    ts_start: datetime,
    ts_end: datetime,
    rate: float,
    population: int = 1,
    exposure: Optional[float] = None,
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
        The average number of events per vehicle per `unit` of time (lambda).
    population : int
        The total number of vehicles in the cohort.
    exposure : float, optional
        The total exposure, defined as `population * duration_in_unit`.
        If provided, `population` and `duration` are ignored for exposure calculation.
    unit : str, optional
        The time unit for the rate (e.g., "second", "hour", "day"), by default "day".

    Returns
    -------
    list[float]
        A list of generated timestamps as Unix timestamps (floats).
    """
    if exposure is None:
        duration_seconds = (ts_end - ts_start).total_seconds()
        if unit == "day":
            duration_in_unit = duration_seconds / (24 * 60 * 60)
        elif unit == "hour":
            duration_in_unit = duration_seconds / (60 * 60)
        elif unit == "minute":
            duration_in_unit = duration_seconds / 60
        elif unit == "second":
            duration_in_unit = duration_seconds
        else:
            raise ValueError(
                "Unsupported time unit. Use 'second', 'minute', 'hour', or 'day'."
            )
        total_exposure = population * duration_in_unit
    else:
        total_exposure = exposure

    mu = rate * total_exposure
    duration_seconds = (ts_end - ts_start).total_seconds()
    if duration_seconds <= 0:
        rate_per_second = 0
    else:
        rate_per_second = mu / duration_seconds

    # For the homogeneous case, we call the sampler once over the whole interval
    return _sample_poisson_interval(
        rate=rate_per_second, start=ts_start, end=ts_end, random_seed=random_seed
    )

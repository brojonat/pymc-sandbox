import numpy as np
import pandas as pd
import pymc as pm


def piecewise_exponential_log_likelihood(
    t, d, boundaries, lambdas, name_prefix: str = ""
):
    """
    Custom log-likelihood for a piecewise exponential model.

    This function calculates the log-likelihood of survival data given a set of
    hazard rates (lambdas) that are constant over specified time intervals.

    Parameters
    ----------
    t : array-like
        Durations (time to event or censoring).
    d : array-like
        Event indicators (1 if event observed, 0 if censored).
    boundaries : array-like
        Time points that define the intervals. Must be sorted. The first interval
        is from 0 to boundaries[0], the second from boundaries[0] to boundaries[1], etc.
    lambdas : array-like or aesara.tensor
        Hazard rates for each interval. Must have length len(boundaries) + 1.
    name_prefix : str, optional
        A prefix for the names of the PyMC distributions.

    Returns
    -------
    aesara.tensor
        The total log-likelihood of the data.
    """
    # Determine which interval each observation falls into
    interval_idx = pm.math.sum(t > boundaries[:, None], axis=0)

    # Get the hazard rate corresponding to each observation's interval
    lambda_t = lambdas[interval_idx]

    # Calculate cumulative hazard up to the start of each interval
    interval_durations = pm.math.concatenate(
        [[boundaries[0]], pm.math.diff(boundaries)]
    )
    cumulative_hazard_parts = interval_durations * lambdas[:-1]

    # Calculate cumulative hazard for each observation
    # 1. Sum of hazards for all full intervals passed
    #    We need a way to do a cumulative sum based on interval_idx.
    #    A scan or a loop is one way, but can be slow. A clever indexing is better.
    #    Let's create a cumulative sum array for the hazard parts.
    cumulative_hazard_prefix = pm.math.concatenate(
        [[0.0], pm.math.cumsum(cumulative_hazard_parts)]
    )
    hazard_sum_full_intervals = cumulative_hazard_prefix[interval_idx]

    # 2. Hazard for the partial final interval
    #    The start time of the interval for each observation `t`
    boundary_starts = pm.math.concatenate([[0.0], boundaries])
    t_start_of_interval = boundary_starts[interval_idx]
    time_in_final_interval = t - t_start_of_interval
    hazard_in_final_interval = lambda_t * time_in_final_interval

    # Total cumulative hazard (Lambda(t))
    cumulative_hazard = hazard_sum_full_intervals + hazard_in_final_interval

    # Log-likelihood calculation
    # log_likelihood = log(lambda_t) * d - cumulative_hazard
    log_likelihood = pm.math.log(lambda_t) * d - cumulative_hazard

    return pm.Potential(f"{name_prefix}log_likelihood", log_likelihood)


def hazard_rate_model(
    duration: np.ndarray,
    observed: np.ndarray,
    num_bins: int = 10,
    lambda_prior_alpha: float = 1.0,
    lambda_prior_beta: float = 1.0,
):
    """
    A Bayesian piecewise exponential survival model.

    This model estimates a hazard rate that is constant over a set of predefined
    time intervals, allowing for non-monotonic hazard functions.

    Parameters
    ----------
    duration : np.ndarray
        An array of observed durations (time-to-event or time-to-censoring).
    observed : np.ndarray
        An array of event indicators (1 if event observed, 0 if censored).
    num_bins : int, optional
        The number of time intervals to divide the data into. Defaults to 10.
    lambda_prior_alpha : float, optional
        The alpha parameter for the Gamma prior on the hazard rates. Defaults to 1.0.
    lambda_prior_beta : float, optional
        The beta parameter for the Gamma prior on the hazard rates. Defaults to 1.0.

    Returns
    -------
    pm.Model
        A PyMC model instance.
    """
    with pm.Model() as model:
        # Define the time boundaries for the piecewise hazard rate
        # We'll use percentiles of the observed failure times to set boundaries,
        # ensuring each interval has data.
        failure_times = duration[observed == 1]
        if len(failure_times) < num_bins:
            # Fallback if there are very few failures
            max_time = np.max(duration) if len(duration) > 0 else 1
            boundaries = np.linspace(0, max_time, num_bins + 1)[1:-1]
        else:
            boundaries = np.percentile(
                failure_times, np.linspace(0, 100, num_bins + 1)
            )[1:-1]

        # Priors for the hazard rate in each interval
        lambdas = pm.Gamma(
            "lambdas",
            alpha=lambda_prior_alpha,
            beta=lambda_prior_beta,
            shape=num_bins,
        )

        # Custom log-likelihood
        piecewise_exponential_log_likelihood(
            t=duration,
            d=observed,
            boundaries=boundaries,
            lambdas=lambdas,
            name_prefix="hazard",
        )

        # Store boundaries in the model for later use in visualization
        pm.Data("boundaries", boundaries)

    return model


def fit_hazard_rate_model(data: pd.DataFrame, **kwargs):
    """Fits a piecewise exponential model to the provided survival data."""
    duration = data["duration"].values
    observed = data["observed"].values
    model = hazard_rate_model(duration, observed, **kwargs)
    with model:
        idata = pm.sample(2000, tune=1000, chains=4, cores=1)

    return idata

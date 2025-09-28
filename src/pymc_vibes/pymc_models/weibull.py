import numpy as np
import pandas as pd
import pymc as pm
from arviz import InferenceData


def generate_weibull_data(
    alpha: float,
    beta: float,
    num_events: int,
    censoring_time: float,
) -> pd.DataFrame:
    """
    Generate synthetic data for a Weibull survival analysis model.

    This function simulates event times from a Weibull distribution and
    introduces right-censoring.

    Parameters
    ----------
    alpha : float
        The shape parameter of the Weibull distribution.
    beta : float
        The scale parameter of the Weibull distribution.
    num_events : int
        The number of subjects or units to simulate.
    censoring_time : float
        The time at which observations are censored. All events that
        would have occurred after this time are considered censored.

    Returns
    -------
    pd.DataFrame
        A DataFrame with two columns:
        - 'duration': The observed time (either event time or censoring time).
        - 'observed': A boolean indicating if the event was observed (True)
          or if the data is censored (False).
    """
    # Generate true event times from a Weibull distribution
    true_event_times = np.random.weibull(a=alpha, size=num_events) * beta

    # Determine observed duration and event status based on censoring
    observed = true_event_times <= censoring_time
    duration = np.minimum(true_event_times, censoring_time)

    return pd.DataFrame({"duration": duration, "observed": observed})


def fit_weibull_model(data: pd.DataFrame) -> InferenceData:
    """
    Fits a Bayesian Weibull survival model to the given data.

    This model is appropriate for right-censored data, where some events
    may not have been observed by the end of the study period.

    Parameters
    ----------
    data : pd.DataFrame
        A DataFrame containing the survival data. It must have two columns:
        - 'duration': The time to an event or censoring.
        - 'observed': A boolean flag, where True indicates that the event was
          observed, and False indicates that the data was censored.

    Returns
    -------
    arviz.InferenceData
        An ArviZ InferenceData object containing the posterior samples,
        log-likelihood, and other model-related information.
    """
    duration = data["duration"].values
    observed = data["observed"].values

    observed_durations = duration[observed]
    censored_durations = duration[~observed]

    with pm.Model() as model:
        # Priors for the Weibull parameters
        alpha = pm.HalfNormal("alpha", sigma=1.0)
        beta = pm.HalfNormal("beta", sigma=10.0)

        # Likelihood for observed events (the PDF of the Weibull distribution)
        # We use a Potential to add the log-likelihood of the observed data
        if observed_durations.size > 0:
            observed_logp = pm.Weibull.logp(observed_durations, alpha=alpha, beta=beta)
            pm.Potential("observed_likelihood", observed_logp.sum())

        # Likelihood for censored events (the survival function)
        # log(S(t)) = -(t / beta) ** alpha
        if censored_durations.size > 0:
            censored_logp = -((censored_durations / beta) ** alpha)
            pm.Potential("censored_likelihood", censored_logp.sum())

        # Sample from the posterior
        idata = pm.sample(2000, tune=1000, chains=4, cores=1, return_inferencedata=True)

    return idata

"""PyMC models for Bernoulli experiments."""

import arviz as az
import pandas as pd
import pymc as pm


def fit_bernoulli_model(
    data: pd.Series,
) -> az.InferenceData:
    """
    Fit a Bayesian Bernoulli model to estimate the success probability.

    Parameters
    ----------
    data : pd.Series
        A series of Bernoulli trials (0s and 1s).

    Returns
    -------
    az.InferenceData
        The ArviZ InferenceData object containing the posterior samples for the
        success probability 'p'.
    """
    with pm.Model() as model:
        # Prior for the success probability 'p'
        p = pm.Beta("p", alpha=1.0, beta=1.0)

        # Likelihood of the observed data
        pm.Bernoulli("likelihood", p=p, observed=data)

        # Sample from the posterior
        idata = pm.sample()

    return idata

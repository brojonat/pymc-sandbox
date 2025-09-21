"""PyMC models for A/B testing."""

import arviz as az
import pandas as pd
import pymc as pm


def fit_ab_model(
    data: pd.DataFrame,
) -> az.InferenceData:
    """
    Fit a Bayesian A/B test model to estimate the conversion rate for multiple variants.

    Parameters
    ----------
    data : pd.DataFrame
        A DataFrame with 'variant' and 'outcome' columns.

    Returns
    -------
    az.InferenceData
        The ArviZ InferenceData object containing the posterior samples for the
        conversion rate 'p' for each variant.
    """
    variants = data["variant"].unique()
    variant_lookup = {name: i for i, name in enumerate(variants)}
    variant_idx = data["variant"].map(variant_lookup).values

    coords = {"variant": variants}

    with pm.Model(coords=coords) as model:
        # Hyperpriors for the Beta distribution
        alpha = pm.HalfCauchy("alpha", beta=10)
        beta = pm.HalfCauchy("beta", beta=10)

        # Prior for the conversion rate 'p' for each variant, drawn from a common Beta distribution
        p = pm.Beta("p", alpha=alpha, beta=beta, dims="variant")

        # Likelihood of the observed data
        pm.Bernoulli("likelihood", p=p[variant_idx], observed=data["outcome"])

        # Sample from the posterior
        idata = pm.sample()

    return idata

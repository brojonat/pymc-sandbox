"""ab_test.py"""

import arviz as az
import ibis
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from mlflow.tracking import MlflowClient
from scipy import stats

from pymc_vibes.pymc_models.ab_test import fit_ab_model
from pymc_vibes.schemas import ABTestPosteriorSummary, PosteriorCurve, PosteriorSummary
from pymc_vibes.server.db import get_db_connection_from_env
from pymc_vibes.server.mlflow import get_mlflow_client
from pymc_vibes.server.mlflow_cache import get_or_create_idata

router = APIRouter(prefix="/ab-test", tags=["a/b test"])


def _calculate_posterior_summary(
    idata, var_name, variant_name=None
) -> PosteriorSummary:
    """Helper function to calculate posterior summary statistics and KDE."""
    if variant_name:
        posterior = idata.posterior[var_name].sel(variant=variant_name)
    else:
        posterior = idata.posterior[var_name]

    posterior_samples = posterior.values.flatten()
    kde = stats.gaussian_kde(posterior_samples)
    x = np.linspace(posterior_samples.min(), posterior_samples.max(), 200)
    y = kde(x)

    summary = az.summary(
        idata.posterior,
        var_names=[var_name],
        coords={"variant": [variant_name]} if variant_name else None,
        hdi_prob=0.94,
        stat_funcs={"median": np.median},
        extend=True,
    )
    return PosteriorSummary(
        stats=summary.to_dict(orient="split"),
        curve=PosteriorCurve(x=x.tolist(), y=y.tolist()),
    )


@router.get("/posterior", response_model=ABTestPosteriorSummary)
def get_posterior(
    experiment_name: str = Query(...),
    conn: ibis.BaseBackend = Depends(get_db_connection_from_env),
    mlflow_client: MlflowClient = Depends(get_mlflow_client),
):
    """Computes and returns a summary of the posterior distribution for an A/B test."""
    # 1. Check if experiment exists
    metadata_table = conn.table("_vibes_experiments_metadata")
    experiment_meta = (
        metadata_table.filter(metadata_table.name == experiment_name).limit(1).execute()
    )
    if experiment_meta.empty:
        raise HTTPException(
            status_code=404, detail=f"Experiment '{experiment_name}' not found."
        )

    # 2. Check if it's an A/B test experiment
    if experiment_meta["type"][0] != "ab-test":
        raise HTTPException(
            status_code=400,
            detail=f"Experiment '{experiment_name}' is not of type 'ab-test'.",
        )

    # 3. Get the trial data
    try:
        table = conn.table(experiment_name)
        data = table.select("variant", "outcome").execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve data: {e}")

    # 4. Fit PyMC model or get from cache
    idata = get_or_create_idata(
        experiment_name=experiment_name,
        data=data,
        model_fit_function=fit_ab_model,
        mlflow_client=mlflow_client,
    )

    # 5. Calculate summaries for each variant
    variant_summaries = {}
    variant_names = idata.posterior["variant"].values
    for variant_name in variant_names:
        variant_summaries[variant_name] = _calculate_posterior_summary(
            idata, "p", variant_name
        )

    return ABTestPosteriorSummary(variants=variant_summaries)

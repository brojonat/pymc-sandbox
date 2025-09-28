"""Weibull experiment routes."""

import arviz as az
import ibis
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from mlflow.tracking import MlflowClient
from scipy import stats

from pymc_vibes.db import get_db_connection_from_env
from pymc_vibes.pymc_models.weibull import fit_weibull_model
from pymc_vibes.schemas import PosteriorCurve, PosteriorSummary
from pymc_vibes.server.mlflow import get_mlflow_client
from pymc_vibes.server.mlflow_cache import get_or_create_idata

router = APIRouter(prefix="/weibull", tags=["weibull"])


@router.get("/posterior")
def get_posterior(
    experiment_name: str = Query(...),
    conn: ibis.BaseBackend = Depends(get_db_connection_from_env),
    mlflow_client: MlflowClient = Depends(get_mlflow_client),
):
    """
    Get the posterior distributions for a Weibull experiment.

    Returns the posterior samples for the alpha and beta parameters of the
    Weibull distribution.
    """
    metadata_table = conn.table("_vibes_experiments_metadata")
    experiment = metadata_table.filter(
        (metadata_table.name == experiment_name) & (metadata_table.type == "weibull")
    ).execute()

    if experiment.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Weibull experiment '{experiment_name}' not found.",
        )

    table = conn.table(experiment_name)
    data = table.execute()

    if data.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for experiment '{experiment_name}'.",
        )

    idata = get_or_create_idata(
        experiment_name=experiment_name,
        data=data,
        model_fit_function=fit_weibull_model,
        mlflow_client=mlflow_client,
    )

    results = {}
    for var in ["alpha", "beta"]:
        posterior_samples = idata.posterior[var].values.flatten()

        # Generate KDE for the posterior curve
        kde = stats.gaussian_kde(posterior_samples)
        x = np.linspace(posterior_samples.min(), posterior_samples.max(), 200)
        y = kde(x)

        # Calculate summary statistics
        summary = az.summary(
            idata,
            var_names=[var],
            hdi_prob=0.94,
            stat_funcs={"median": np.median},
            extend=True,
        )

        results[var] = PosteriorSummary(
            stats=summary.to_dict(orient="split"),
            curve=PosteriorCurve(x=x.tolist(), y=y.tolist()),
        )

    return results

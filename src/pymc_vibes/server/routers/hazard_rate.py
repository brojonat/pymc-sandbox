"""Hazard Rate experiment routes."""

import arviz as az
import ibis
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from mlflow.tracking import MlflowClient

from pymc_vibes.db import get_db_connection_from_env
from pymc_vibes.pymc_models.hazard_rate import fit_hazard_rate_model
from pymc_vibes.server.mlflow import get_mlflow_client
from pymc_vibes.server.mlflow_cache import get_or_create_idata

router = APIRouter(prefix="/hazard-rate", tags=["hazard-rate"])


@router.get("/posterior")
def get_posterior(
    experiment_name: str = Query(...),
    conn: ibis.BaseBackend = Depends(get_db_connection_from_env),
    mlflow_client: MlflowClient = Depends(get_mlflow_client),
):
    """
    Get the posterior distributions for a Hazard Rate experiment.

    Returns the posterior samples for the lambda parameters of the
    piecewise exponential hazard rate model.
    """
    metadata_table = conn.table("_vibes_experiments_metadata")
    experiment = metadata_table.filter(
        (metadata_table.name == experiment_name)
        & (metadata_table.type == "hazard-rate")
    ).execute()

    if experiment.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Hazard Rate experiment '{experiment_name}' not found.",
        )

    table = conn.table(experiment_name)
    data = table.execute()

    if data.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for experiment '{experiment_name}'.",
        )

    # Note: Unlike the Weibull model, the hazard rate model's structure
    # (i.e., the boundaries) depends on the data. Caching is still beneficial
    # for re-runs on the *exact same* data, but if the data changes, a new
    # model structure and new fit are required. `get_or_create_idata` handles
    # this by checking a hash of the data.
    idata = get_or_create_idata(
        experiment_name=experiment_name,
        data=data,
        model_fit_function=fit_hazard_rate_model,
        mlflow_client=mlflow_client,
    )

    # Extract lambdas and boundaries
    posterior_lambdas = idata.posterior["lambdas"]
    boundaries = idata.constant_data["boundaries"].values

    # Calculate summary statistics for lambdas
    summary = az.summary(
        idata,
        var_names=["lambdas"],
        hdi_prob=0.94,
        stat_funcs={"median": np.median},
        extend=True,
    )

    # We need to structure the response so the frontend knows the time intervals
    # associated with each lambda.
    # The response will include the lambda posterior summaries and the boundaries.
    results = {
        "lambdas": summary.to_dict(orient="split"),
        "boundaries": boundaries.tolist(),
    }

    return results

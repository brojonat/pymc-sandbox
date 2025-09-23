"""bernoulli.py"""

import arviz as az
import ibis
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from mlflow.tracking import MlflowClient
from scipy import stats

from pymc_vibes.db import get_db_connection_from_env
from pymc_vibes.pymc_models.bernoulli import fit_bernoulli_model
from pymc_vibes.schemas import PosteriorCurve, PosteriorSummary
from pymc_vibes.server.mlflow import get_mlflow_client
from pymc_vibes.server.mlflow_cache import get_or_create_idata

router = APIRouter(prefix="/bernoulli", tags=["bernoulli"])


@router.get("/posterior", response_model=PosteriorSummary)
def get_bernoulli_posterior(
    experiment_name: str = Query(...),
    conn: ibis.BaseBackend = Depends(get_db_connection_from_env),
    mlflow_client: MlflowClient = Depends(get_mlflow_client),
):
    """
    Computes and returns a summary of the posterior distribution for a Bernoulli experiment.
    """
    # 1. Check if experiment exists
    metadata_table = conn.table("_vibes_experiments_metadata")
    experiment_meta = (
        metadata_table.filter(metadata_table.name == experiment_name).limit(1).execute()
    )
    if experiment_meta.empty:
        raise HTTPException(
            status_code=404, detail=f"Experiment '{experiment_name}' not found."
        )

    # 2. Check if it's a Bernoulli experiment
    if experiment_meta["type"][0] != "bernoulli":
        raise HTTPException(
            status_code=400,
            detail=f"Experiment '{experiment_name}' is not of type 'bernoulli'.",
        )

    # 3. Get the trial data
    try:
        table = conn.table(experiment_name)
        # Assuming the 'outcome' column contains boolean/integer (0 or 1) data
        outcomes = table.outcome.execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve data: {e}")

    idata = get_or_create_idata(
        experiment_name=experiment_name,
        data=outcomes,
        model_fit_function=fit_bernoulli_model,
        mlflow_client=mlflow_client,
    )

    posterior_samples = idata.posterior["p"].values.flatten()

    # Generate KDE for the posterior curve using a numerical approach
    kde = stats.gaussian_kde(posterior_samples)
    x = np.linspace(posterior_samples.min(), posterior_samples.max(), 200)
    y = kde(x)

    # Calculate summary statistics
    summary = az.summary(
        idata,
        var_names=["p"],
        hdi_prob=0.94,
        stat_funcs={"median": np.median},
        extend=True,
    )

    return PosteriorSummary(
        stats=summary.to_dict(orient="split"),
        curve=PosteriorCurve(x=x.tolist(), y=y.tolist()),
    )

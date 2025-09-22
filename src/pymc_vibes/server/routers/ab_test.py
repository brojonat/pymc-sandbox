"""ab_test.py"""

import ibis
from fastapi import APIRouter, Depends, HTTPException, Query
from mlflow.tracking import MlflowClient

from pymc_vibes.pymc_models.ab_test import fit_ab_model
from pymc_vibes.server.db import get_db_connection_from_env
from pymc_vibes.server.mlflow import get_mlflow_client
from pymc_vibes.server.mlflow_cache import get_or_create_idata

router = APIRouter(prefix="/ab-test", tags=["a/b test"])


@router.get("/posterior")
async def get_posterior(
    experiment_name: str = Query(...),
    conn: ibis.BaseBackend = Depends(get_db_connection_from_env),
    mlflow_client: MlflowClient = Depends(get_mlflow_client),
):
    """Returns posterior samples for an A/B test experiment."""
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

    # 5. Format posterior samples for the frontend
    posterior_samples = {}
    for variant_name in idata.posterior["variant"].values:
        posterior_samples[variant_name] = (
            idata.posterior["p"].sel(variant=variant_name).values.flatten().tolist()
        )

    return {"posterior_samples": posterior_samples}

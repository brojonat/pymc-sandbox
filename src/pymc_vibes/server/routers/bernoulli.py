"""bernoulli.py"""

import ibis
from fastapi import APIRouter, Depends, HTTPException, Query

from pymc_vibes.db import get_db_connection_from_env
from pymc_vibes.pymc_models.bernoulli import fit_bernoulli_model

router = APIRouter(prefix="/bernoulli", tags=["bernoulli"])


@router.get("/posterior")
async def get_bernoulli_posterior(
    experiment_name: str = Query(...),
    conn: ibis.BaseBackend = Depends(get_db_connection_from_env),
):
    """Returns posterior samples for a Bernoulli experiment."""
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

    # 4. Fit PyMC model
    idata = fit_bernoulli_model(outcomes)

    posterior_samples = idata.posterior["p"].values.flatten().tolist()

    return {"posterior_samples": posterior_samples}

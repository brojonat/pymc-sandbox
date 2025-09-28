"""Multi-armed bandit experiment routes."""

from typing import Any

import ibis
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from pymc_vibes.pymc_models.multi_armed_bandits import (
    _get_posterior_samples,
    fit_multi_armed_bandit,
    thompson_sampling,
)
from pymc_vibes.server.db import get_db_connection_from_env

router = APIRouter(prefix="/multi-armed-bandits", tags=["multi-armed-bandits"])


def _get_bandit_data(experiment_name: str, conn: ibis.BaseBackend) -> dict[str, Any]:
    """
    Helper function to fetch and process data for a multi-armed bandit experiment.
    """
    metadata_table = conn.table("_vibes_experiments_metadata")
    experiment = metadata_table.filter(
        (metadata_table.name == experiment_name)
        & (metadata_table.type == "multi-armed-bandits")
    ).execute()

    if experiment.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Multi-armed bandit experiment '{experiment_name}' not found.",
        )

    table = conn.table(experiment_name)
    data = table.execute()

    if data.empty:
        return {"arms": []}

    # 1. Infer payout magnitude for each arm from the data
    magnitudes = data[data["reward"] > 0].groupby("arm")["reward"].max()

    # 2. Transform reward data into binary 'outcome'
    data["outcome"] = data.apply(
        lambda row: 1 if row["reward"] == magnitudes.get(row["arm"]) else 0, axis=1
    )

    # 3. Fit the Beta-Bernoulli model on the success probability
    posteriors = fit_multi_armed_bandit(data)

    # 4. Perform Thompson sampling on the expected reward (prob * magnitude)
    prob_best = thompson_sampling(posteriors, magnitudes)

    # 5. Generate posterior samples for frontend plotting
    posterior_samples = _get_posterior_samples(posteriors, magnitudes)

    # 6. Combine results for the response
    results = (
        posteriors.join(prob_best).join(magnitudes.rename("magnitude")).reset_index()
    )
    results["est_prob"] = results["alpha"] / (results["alpha"] + results["beta"])
    results["expected_reward"] = results["est_prob"] * results["magnitude"]

    # Add posterior samples to the results
    results["posterior_samples"] = results["arm"].map(posterior_samples)

    return {"arms": results.to_dict(orient="records")}


@router.get("/posterior")
def get_posterior(
    experiment_name: str = Query(...),
    conn: ibis.BaseBackend = Depends(get_db_connection_from_env),
) -> dict[str, Any]:
    """
    Get the posterior distributions for a multi-armed bandit experiment.

    Returns the alpha and beta parameters for each arm's Beta distribution,
    the expected reward, and the probability of each arm being the best.
    """
    return _get_bandit_data(experiment_name, conn)


@router.get("/next-arm")
def get_next_arm(
    experiment_name: str = Query(...),
    conn: ibis.BaseBackend = Depends(get_db_connection_from_env),
) -> dict[str, Any]:
    """
    Get the next arm to pull using Thompson Sampling.

    This endpoint returns the arm with the highest probability of being the best,
    guiding an optimal decision-making strategy.
    """
    results = _get_bandit_data(experiment_name, conn)
    if not results["arms"]:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for experiment '{experiment_name}'. Cannot recommend an arm.",
        )

    arms_df = pd.DataFrame(results["arms"])
    best_arm = arms_df.loc[arms_df["prob_best"].idxmax()]

    return {"next_arm": best_arm.to_dict()}

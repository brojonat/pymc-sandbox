"""poisson_cohorts.py"""

from datetime import datetime
from typing import Any, Optional

import ibis
from fastapi import APIRouter, Depends, HTTPException, Query

from pymc_vibes.pymc_models.poisson import fit_poisson_rate
from pymc_vibes.server.db import get_db_connection_from_env

router = APIRouter(prefix="/poisson-cohorts", tags=["poisson-cohorts"])


# -------------------------
# Routes
# -------------------------
@router.get("/posterior")
async def get_posterior(
    experiment_name: str = Query(...),
    start: datetime = Query(...),
    end: datetime = Query(...),
    cohort: Optional[list[str]] = Query(default=None),
    event: Optional[list[str]] = Query(default=None),
    model: str = Query(default="poisson"),
    conn: ibis.BaseBackend = Depends(get_db_connection_from_env),
) -> dict[str, Any]:
    """Fit a Poisson rate model for a given experiment and time range."""
    if model != "poisson":
        raise HTTPException(status_code=400, detail=f"Model '{model}' not supported.")

    metadata_table = conn.table("_vibes_experiments_metadata")
    experiment = metadata_table.filter(
        (metadata_table.name == experiment_name)
        & (metadata_table.type == "poisson-cohorts")
    ).execute()
    if experiment.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Poisson cohorts experiment '{experiment_name}' not found.",
        )

    table = conn.table(experiment_name)

    filters = [table.ts >= start, table.ts < end]
    if cohort:
        filters.append(table.cohort.isin(cohort))
    if event:
        filters.append(table.event.isin(event))

    combined_filter = filters[0]
    for f in filters[1:]:
        combined_filter &= f
    table = table.filter(combined_filter)

    results_df = table.execute()
    if results_df.empty:
        return {"results": {}}

    results: dict[str, Any] = {}
    for cohort_name, cohort_df in results_df.groupby("cohort"):
        event_timestamps = cohort_df["ts"]
        idata = fit_poisson_rate(event_timestamps, ts_start=start, ts_end=end)
        results[cohort_name] = {
            "posterior_rate": idata.posterior["rate"].values.flatten().tolist()
        }

    return {"results": results}


@router.get("/list")
async def list_events(
    experiment_name: str = Query(...),
    cohort: Optional[str] = Query(default=None),
    event: Optional[str] = Query(default=None),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=100000),
    offset: int = Query(default=0, ge=0),
    conn: ibis.BaseBackend = Depends(get_db_connection_from_env),
) -> dict[str, Any]:
    """List events for a given Poisson cohorts experiment."""
    metadata_table = conn.table("_vibes_experiments_metadata")
    experiment = metadata_table.filter(
        (metadata_table.name == experiment_name)
        & (metadata_table.type == "poisson-cohorts")
    ).execute()
    if experiment.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Poisson cohorts experiment '{experiment_name}' not found.",
        )

    table = conn.table(experiment_name)

    filters = []
    if cohort:
        filters.append(table.cohort == cohort)
    if event:
        filters.append(table.event == event)
    if start:
        filters.append(table.ts >= start)
    if end:
        filters.append(table.ts < end)

    if filters:
        combined_filter = filters[0]
        for f in filters[1:]:
            combined_filter &= f
        table = table.filter(combined_filter)

    query = table.order_by("ts").limit(limit, offset=offset)
    results_df = query.execute()

    return {
        "rows": results_df.to_dict("records"),
        "count": len(results_df),
        "offset": offset,
    }


@router.delete("/delete")
async def delete_endpoint(
    experiment_name: str = Query(...),
    cohort: Optional[str] = Query(default=None),
    event: Optional[str] = Query(default=None),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    conn: ibis.BaseBackend = Depends(get_db_connection_from_env),
) -> dict[str, Any]:
    """Delete events from a given Poisson cohorts experiment based on filters."""
    if all(v is None for v in (cohort, event, start, end)):
        raise HTTPException(
            status_code=400,
            detail="Provide at least one filter (cohort, event, start, end) to delete.",
        )

    metadata_table = conn.table("_vibes_experiments_metadata")
    experiment = metadata_table.filter(
        (metadata_table.name == experiment_name)
        & (metadata_table.type == "poisson-cohorts")
    ).execute()
    if experiment.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Poisson cohorts experiment '{experiment_name}' not found.",
        )

    table = conn.table(experiment_name)
    filters = []
    if cohort:
        filters.append(table.cohort == cohort)
    if event:
        filters.append(table.event == event)
    if start:
        filters.append(table.ts >= start)
    if end:
        filters.append(table.ts < end)

    combined_filter = filters[0]
    for f in filters[1:]:
        combined_filter &= f

    to_delete_expr = table.filter(combined_filter)
    deleted_count = to_delete_expr.count().execute()

    delete_query = f"DELETE FROM {experiment_name}"
    conditions_sql = []
    params = []

    if cohort:
        conditions_sql.append("cohort = ?")
        params.append(cohort)
    if event:
        conditions_sql.append("event = ?")
        params.append(event)
    if start:
        conditions_sql.append("ts >= ?")
        params.append(start)
    if end:
        conditions_sql.append("ts < ?")
        params.append(end)

    if conditions_sql:
        delete_query += " WHERE " + " AND ".join(conditions_sql)

    conn.con.execute(delete_query, parameters=params)

    return {"deleted": int(deleted_count)}

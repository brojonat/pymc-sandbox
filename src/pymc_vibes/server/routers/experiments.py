"""Router for managing experiments in DuckLake."""

from datetime import datetime
from typing import Any, Optional

import ibis
import pyarrow as pa
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from pymc_vibes.db import get_db_connection_from_env

router = APIRouter(prefix="/experiments", tags=["experiments"])


class ExperimentCreateRequest(BaseModel):
    experiment_name: str
    experiment_type: str
    display_name: str
    initial_data: list[dict[str, Any]]


@router.get("")
async def list_experiments():
    """List all experiments from the metadata table."""
    con = get_db_connection_from_env()
    metadata_table = con.table("_vibes_experiments_metadata")
    results = metadata_table.execute()

    # Ibis/DuckDB may not return timestamps in a JSON-serializable format
    results["created_at"] = results["created_at"].dt.strftime("%Y-%m-%dT%H:%M:%S.%f")
    return {"experiments": results.to_dict("records")}


@router.post("")
async def create_experiment(payload: ExperimentCreateRequest):
    """
    Create a new experiment by creating a new table in DuckLake and
    adding a corresponding record to the metadata table.
    """
    con = get_db_connection_from_env()

    if payload.experiment_name in con.list_tables():
        raise HTTPException(
            status_code=409,
            detail=f"Experiment table '{payload.experiment_name}' already exists.",
        )

    try:
        # Validate the provided data
        if not payload.initial_data:
            raise ValueError("initial_data must contain a non-empty array of objects.")
        arrow_table = pa.Table.from_pylist(payload.initial_data)

        # Use a transaction to ensure both table and metadata are created
        con.con.execute("BEGIN TRANSACTION;")
        try:
            # Create the data table
            con.create_table(payload.experiment_name, obj=arrow_table)

            # Insert a record into the metadata table
            metadata = {
                "name": payload.experiment_name,
                "type": payload.experiment_type,
                "display_name": payload.display_name,
                "status": "created",
                "created_at": datetime.now(),
            }
            con.insert("_vibes_experiments_metadata", [metadata])
            con.con.execute("COMMIT;")
        except Exception as e:
            con.con.execute("ROLLBACK;")
            # Attempt to roll back by dropping the table if it was created
            if payload.experiment_name in con.list_tables():
                con.drop_table(payload.experiment_name, force=True)
            raise HTTPException(
                status_code=500, detail=f"Failed to create experiment: {e}"
            )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid initial data: {e}")
    except Exception as e:
        # This will catch the re-raised exception from the transaction block
        raise HTTPException(status_code=500, detail=f"Failed to create experiment: {e}")

    return {
        "message": "Experiment created successfully",
        "experiment_name": payload.experiment_name,
    }


@router.get("/data")
async def inspect_experiment(
    experiment_name: str = Query(...),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
    conn: ibis.BaseBackend = Depends(get_db_connection_from_env),
):
    """Inspect the data for a given experiment with optional filters."""
    # 1. Check if experiment exists in metadata
    metadata_table = conn.table("_vibes_experiments_metadata")
    if (
        metadata_table.filter(metadata_table.name == experiment_name).count().execute()
        == 0
    ):
        raise HTTPException(
            status_code=404,
            detail=f"Experiment '{experiment_name}' not found.",
        )

    # 2. Get the table and apply filters
    table = conn.table(experiment_name)

    # Time-range filters are only applied if a 'timestamp' column exists
    filters = []
    if "timestamp" in table.columns:
        timestamp_col = table.timestamp.cast("timestamp")
        if start:
            filters.append(timestamp_col >= start)
        if end:
            filters.append(timestamp_col < end)

    if filters:
        combined_filter = filters[0]
        for f in filters[1:]:
            combined_filter &= f
        table = table.filter(combined_filter)

    # 3. Get total count for pagination info before applying limit
    total_count = table.count().execute()

    # 4. Apply limit and offset
    query = table.limit(limit, offset=offset)
    results_df = query.execute()

    # 5. Return data
    return {
        "rows": results_df.to_dict("records"),
        "count": len(results_df),
        "total_count": int(total_count),
        "offset": offset,
        "limit": limit,
    }


@router.delete("")
async def delete_experiment(experiment_name: str = Query(...)):
    """
    Delete an experiment by dropping its data table and removing its
    record from the metadata table.
    """
    con = get_db_connection_from_env()

    # Check if the experiment exists in metadata
    metadata_table = con.table("_vibes_experiments_metadata")
    if (
        metadata_table.filter(metadata_table.name == experiment_name).count().execute()
        == 0
    ):
        raise HTTPException(
            status_code=404,
            detail=f"Experiment '{experiment_name}' not found in metadata.",
        )

    try:
        con.con.execute("BEGIN TRANSACTION;")
        try:
            # Delete from metadata
            con.con.execute(
                f"DELETE FROM _vibes_experiments_metadata WHERE name = '{experiment_name}'"
            )

            # Drop the data table
            if experiment_name in con.list_tables():
                con.drop_table(experiment_name)
            con.con.execute("COMMIT;")
        except Exception as e:
            con.con.execute("ROLLBACK;")
            raise HTTPException(
                status_code=500, detail=f"Failed to delete experiment: {e}"
            )

    except Exception as e:
        # Transactions should handle rollback, but we raise an error if something goes wrong
        raise HTTPException(status_code=500, detail=f"Failed to delete experiment: {e}")

    return

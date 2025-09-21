"""Router for handling event data."""

from typing import Any, Dict, List

import duckdb
import ibis
import pyarrow as pa
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from pymc_vibes.db import get_db_connection_from_env

log = structlog.get_logger()
router = APIRouter(prefix="/events", tags=["events"])


@router.post("")
async def upload_events(
    events: List[Dict[str, Any]],
    experiment_name: str = Query(...),
    conn: ibis.BaseBackend = Depends(get_db_connection_from_env),
):
    """Upload a batch of events to a specific experiment."""
    if experiment_name not in conn.list_tables():
        raise HTTPException(
            status_code=404, detail=f"Experiment '{experiment_name}' not found."
        )

    try:
        # Convert the list of dicts to a PyArrow Table for insertion
        table = pa.Table.from_pylist(events)
        conn.insert(experiment_name, obj=table)
    except (
        duckdb.ConstraintException,
        duckdb.BinderException,
        duckdb.InvalidInputException,
        pa.ArrowInvalid,
        ValueError,
    ) as e:
        log.warning(
            "event.upload.bad_request",
            error=str(e),
            experiment_name=experiment_name,
        )
        raise HTTPException(
            status_code=400,
            detail="Invalid event data. This may be due to a schema mismatch "
            "(e.g., wrong column names, data types) or a constraint violation.",
        )
    except Exception as e:
        log.error(
            "event.upload.failed",
            error=str(e),
            experiment_name=experiment_name,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while inserting event data.",
        )

    return {
        "message": f"Successfully uploaded {len(events)} events to '{experiment_name}'.",
    }

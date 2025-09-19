"""Router for handling event data."""

from typing import Any, Dict, List

import pyarrow as pa
from fastapi import APIRouter, HTTPException

from pymc_vibes.server.database import get_db_connection

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/{experiment_name}")
async def upload_events(experiment_name: str, events: List[Dict[str, Any]]):
    """
    Endpoint to upload a batch of events to a specific experiment (table).
    """
    con = get_db_connection()

    # 1. Validate that the experiment table exists
    if experiment_name not in con.list_tables():
        raise HTTPException(
            status_code=404, detail=f"Experiment '{experiment_name}' not found."
        )

    # 2. Insert the event data into the table
    try:
        # Convert the list of dicts to a PyArrow Table for insertion
        table = pa.Table.from_pylist(events)
        con.insert(experiment_name, obj=table)
    except Exception as e:
        # In a real app, you would have more specific error handling and logging
        # This could fail due to schema mismatch, for example.
        raise HTTPException(status_code=500, detail=f"Failed to insert event data: {e}")

    return {
        "message": f"Successfully uploaded {len(events)} events to '{experiment_name}'.",
    }

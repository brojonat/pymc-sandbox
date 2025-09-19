"""Router for managing experiments in DuckLake."""

import json
from datetime import datetime

import pyarrow as pa
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from pymc_vibes.server.database import get_db_connection

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("/")
async def list_experiments():
    """List all experiments from the metadata table."""
    con = get_db_connection()
    metadata_table = con.table("_vibes_experiments_metadata")
    results = metadata_table.execute()

    # Ibis/DuckDB may not return timestamps in a JSON-serializable format
    results["created_at"] = results["created_at"].dt.strftime("%Y-%m-%dT%H:%M:%S.%f")
    return {"experiments": results.to_dict("records")}


@router.post("/")
async def create_experiment(
    experiment_name: str = Form(...),
    experiment_type: str = Form(...),
    display_name: str = Form(...),
    initial_data: UploadFile = File(...),
):
    """
    Create a new experiment by creating a new table in DuckLake and
    adding a corresponding record to the metadata table.
    """
    con = get_db_connection()

    if experiment_name in con.list_tables():
        raise HTTPException(
            status_code=409,
            detail=f"Experiment table '{experiment_name}' already exists.",
        )

    try:
        # Read and validate the uploaded JSON file
        contents = await initial_data.read()
        data = json.loads(contents)
        if not isinstance(data, list) or not data:
            raise ValueError("JSON file must contain a non-empty array of objects.")
        arrow_table = pa.Table.from_pylist(data)

        # Use a transaction to ensure both table and metadata are created
        with con.begin():
            # Create the data table
            con.create_table(experiment_name, obj=arrow_table)

            # Insert a record into the metadata table
            metadata = {
                "name": experiment_name,
                "type": experiment_type,
                "display_name": display_name,
                "status": "created",
                "created_at": datetime.now(),
            }
            con.insert("_vibes_experiments_metadata", [metadata])

    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON data: {e}")
    except Exception as e:
        # Attempt to roll back by dropping the table if it was created
        if experiment_name in con.list_tables():
            con.drop_table(experiment_name, force=True)
        raise HTTPException(status_code=500, detail=f"Failed to create experiment: {e}")

    return {
        "message": "Experiment created successfully",
        "experiment_name": experiment_name,
    }


@router.delete("/{experiment_name}", status_code=204)
async def delete_experiment(experiment_name: str):
    """
    Delete an experiment by dropping its data table and removing its
    record from the metadata table.
    """
    con = get_db_connection()

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
        with con.begin():
            # Delete from metadata
            metadata_table = metadata_table.filter(
                metadata_table.name != experiment_name
            )
            con.execute(
                f"DELETE FROM _vibes_experiments_metadata WHERE name = '{experiment_name}'"
            )

            # Drop the data table
            if experiment_name in con.list_tables():
                con.drop_table(experiment_name)

    except Exception as e:
        # Transactions should handle rollback, but we raise an error if something goes wrong
        raise HTTPException(status_code=500, detail=f"Failed to delete experiment: {e}")

    return

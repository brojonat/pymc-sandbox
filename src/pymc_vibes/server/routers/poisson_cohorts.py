"""poisson_cohorts.py"""

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import ibis
import pandas as pd
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()


# -------------------------
# Storage (Ibis on DuckDB)
# -------------------------
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DB_FILE = DATA_DIR / "poisson-cohorts.db"
EVENTS_TABLE = "events"


def get_ibis_conn():
    """FastAPI dependency to manage Ibis connections to DuckDB."""
    if not DB_FILE.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Database file not found at {DB_FILE}. Run 'pv migrations init-db' to initialize it.",
        )
    conn = ibis.duckdb.connect(database=str(DB_FILE))
    if EVENTS_TABLE not in conn.list_tables():
        raise HTTPException(
            status_code=500,
            detail=f"Table '{EVENTS_TABLE}' not found in the database. Run 'pv migrations init-db' to create it.",
        )
    yield conn


# -------------------------
# Schemas
# -------------------------
class EventRow(BaseModel):
    ts: datetime = Field(..., description="ISO8601 timestamp of the event")
    cohort: str = Field(..., min_length=1)
    event: str = Field(..., min_length=1)


class UploadRequest(BaseModel):
    rows: list[EventRow]


class UploadResponse(BaseModel):
    ingested: int


# -------------------------
# Routes
# -------------------------
@router.post("/poisson-cohorts/upload", response_model=UploadResponse)
async def upload_events(
    payload: UploadRequest = Body(...), conn: ibis.BaseBackend = Depends(get_ibis_conn)
) -> UploadResponse:
    if not payload.rows:
        return UploadResponse(ingested=0)

    df = pd.DataFrame([row.dict() for row in payload.rows])
    conn.insert(EVENTS_TABLE, df)

    return UploadResponse(ingested=len(payload.rows))


@router.get("/poisson-cohorts/list")
async def list_events(
    cohort: Optional[str] = Query(default=None),
    event: Optional[str] = Query(default=None),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=100000),
    offset: int = Query(default=0, ge=0),
    conn: ibis.BaseBackend = Depends(get_ibis_conn),
) -> dict[str, Any]:
    table = conn.table(EVENTS_TABLE)

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

    return {"rows": results_df.to_dict("records"), "count": len(results_df), "offset": offset}


@router.delete("/poisson-cohorts/delete")
async def delete_endpoint(
    cohort: Optional[str] = Query(default=None),
    event: Optional[str] = Query(default=None),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    conn: ibis.BaseBackend = Depends(get_ibis_conn),
) -> dict[str, Any]:
    if all(v is None for v in (cohort, event, start, end)):
        raise HTTPException(
            status_code=400,
            detail="Provide at least one filter (cohort, event, start, end) to delete.",
        )

    table = conn.table(EVENTS_TABLE)
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

    delete_query = f"DELETE FROM {EVENTS_TABLE}"
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

    conn.sql(delete_query, params=params)

    return {"deleted": deleted_count}

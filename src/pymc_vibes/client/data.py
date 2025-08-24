"""Data subcommand for the CLI."""

import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import ibis
import pandas as pd

from pymc_vibes.pymc_models.poisson import generate_poisson_events

# Database connection details (mirroring the server)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_FILE = DATA_DIR / "poisson-cohorts.db"
EVENTS_TABLE = "events"


@contextmanager
def ibis_connection():
    """Context manager for an Ibis DuckDB connection."""
    if not DB_FILE.exists():
        raise click.UsageError(
            f"Database file not found at {DB_FILE}.\nRun 'pv migrations init-db' to initialize it."
        )
    conn = ibis.duckdb.connect(database=str(DB_FILE))
    try:
        if EVENTS_TABLE not in conn.list_tables():
            raise click.UsageError(
                f"Table '{EVENTS_TABLE}' not found in the database.\n"
                "Run 'pv migrations init-db' to create it."
            )
        yield conn
    finally:
        # Ibis backend connections are managed by the ibis library
        # and don't need to be explicitly closed.
        pass


@click.group()
def data():
    """Commands for interacting with the events database."""
    pass


@data.command()
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    required=True,
    help="Path to a JSON file with an array of event objects.",
)
def upload(file: str):
    """Upload events from a JSON file."""
    try:
        with open(file, "r", encoding="utf-8") as f:
            rows = json.load(f)
        if not isinstance(rows, list):
            raise click.UsageError("JSON file must contain a list of event objects.")
        df = pd.DataFrame(rows)
        if not all(col in df.columns for col in ["ts", "cohort", "event"]):
            raise click.UsageError(
                "Each event object in the JSON file must contain 'ts', 'cohort', and 'event' keys."
            )
        df["ts"] = pd.to_datetime(df["ts"])
    except (json.JSONDecodeError, KeyError, Exception) as e:
        raise click.UsageError(f"Failed to read or parse JSON file: {e}")

    with ibis_connection() as conn:
        conn.insert(EVENTS_TABLE, df)
    click.echo(f"Successfully ingested {len(df)} events from {file}.")


@data.command(name="list")
@click.option("--cohort", type=str, help="Filter by cohort.")
@click.option("--event", type=str, help="Filter by event type.")
@click.option("--start", type=click.DateTime(), help="Start timestamp (ISO format).")
@click.option("--end", type=click.DateTime(), help="End timestamp (ISO format).")
@click.option("--limit", type=int, default=100, help="Maximum number of records to return.")
@click.option("--offset", type=int, default=0, help="Number of records to skip.")
def list_events(
    cohort: Optional[str],
    event: Optional[str],
    start: Optional[datetime],
    end: Optional[datetime],
    limit: int,
    offset: int,
):
    """List events from the database with optional filters."""
    with ibis_connection() as conn:
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

        query = table.order_by(ibis.desc("ts")).limit(limit, offset=offset)
        results_df = query.execute()

    if results_df.empty:
        click.echo("No events found matching the criteria.")
    else:
        click.echo(results_df.to_string(index=False))


@data.command()
@click.option(
    "--spec",
    "-s",
    type=click.File("r"),
    default="-",
    help="Path to a JSON spec file for data generation. Defaults to stdin.",
)
@click.option(
    "--out",
    "-o",
    type=click.File("w"),
    default="-",
    help="Path to write the generated data. Defaults to stdout.",
)
@click.option("--seed", type=int, help="Random seed for reproducibility.")
def generate(spec: click.utils.LazyFile, out: click.utils.LazyFile, seed: Optional[int]):
    """Generate a synthetic dataset based on a JSON specification."""
    try:
        spec_data = json.load(spec)
    except Exception as e:
        raise click.UsageError(f"Failed to read or parse spec JSON: {e}")

    all_events = []
    for i, item in enumerate(spec_data):
        try:
            cohort = item["cohort"]
            event = item["event"]
            ts_start = datetime.fromisoformat(item["ts_start"])
            ts_end = datetime.fromisoformat(item["ts_end"])
            model_spec = item["model"]
            method = model_spec["method"]
        except (KeyError, TypeError) as e:
            raise click.UsageError(f"Invalid spec item, missing key: {e}. Item: {item}")

        if ts_start >= ts_end:
            raise click.UsageError(f"ts_start must be before ts_end. Item: {item}")

        if method != "poisson":
            raise click.UsageError(
                f"Unsupported model method '{method}'. Only 'poisson' is supported. Item: {item}"
            )

        try:
            rate = float(model_spec["rate"])
            unit = model_spec.get("unit", "day")
            if rate < 0:
                raise ValueError("Rate must be non-negative.")
        except (KeyError, TypeError, ValueError) as e:
            raise click.UsageError(
                f"Invalid 'poisson' model spec: must include a non-negative 'rate'. Error: {e}. Item: {item}"
            )

        cohort_seed = seed + i if seed is not None else None
        generated_timestamps = generate_poisson_events(
            ts_start=ts_start, ts_end=ts_end, rate=rate, unit=unit, random_seed=cohort_seed
        )

        for ts_unix in generated_timestamps:
            ts = datetime.fromtimestamp(ts_unix).isoformat() + "Z"
            all_events.append({"ts": ts, "cohort": cohort, "event": event})

    json.dump(all_events, out, indent=2)


@data.command()
@click.option("--cohort", type=str, help="Filter by cohort to delete.")
@click.option("--event", type=str, help="Filter by event type to delete.")
@click.option("--start", type=click.DateTime(), help="Start timestamp for deletion range.")
@click.option("--end", type=click.DateTime(), help="End timestamp for deletion range.")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
def delete(
    cohort: Optional[str],
    event: Optional[str],
    start: Optional[datetime],
    end: Optional[datetime],
    yes: bool,
):
    """Delete events from the database with optional filters."""
    if all(v is None for v in (cohort, event, start, end)):
        raise click.UsageError(
            "Provide at least one filter (--cohort, --event, --start, --end) to delete."
        )

    with ibis_connection() as conn:
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

        if deleted_count == 0:
            click.echo("No events found to delete.")
            return

        if not yes:
            click.confirm(
                f"This will permanently delete {deleted_count} events. Continue?", abort=True
            )

        delete_query = f"DELETE FROM {EVENTS_TABLE}"
        conditions_sql, params = [], []
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

        # The ibis backend's `sql` method is for building expressions, not execution.
        # To execute a raw DML statement with parameters, we access the underlying
        # duckdb connection object (`.con`) and use its `execute` method.
        conn.con.execute(delete_query, parameters=params)

    click.echo(f"Successfully deleted {deleted_count} events.")

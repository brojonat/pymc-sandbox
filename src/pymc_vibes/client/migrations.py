"""Migrations subcommand for the CLI."""

from pathlib import Path

import click
import ibis

# Database connection details (mirroring the server and data modules)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_FILE = DATA_DIR / "poisson-cohorts.db"
EVENTS_TABLE = "events"


@click.group()
def migrations():
    """Commands for database schema management."""
    pass


@migrations.command(name="init-db")
def init_db():
    """Initialize the database and create the events table if it doesn't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = ibis.duckdb.connect(database=str(DB_FILE))
    click.echo(f"Initializing database at {DB_FILE}...")
    # Use the underlying raw connection for DDL (Data Definition Language) statements
    conn.con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {EVENTS_TABLE} (
            ts TIMESTAMP,
            cohort VARCHAR,
            event VARCHAR
        );
    """
    )
    click.echo(f"Table '{EVENTS_TABLE}' created or already exists.")

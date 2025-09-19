"""Database connection and schema management."""

import ibis

# In a real application, this would come from a config file.
DUCKLAKE_PATH = "pymc-vibes.ducklake"


def get_db_connection():
    """
    Returns an Ibis connection to the DuckLake database.

    This function connects to DuckDB, loads the DuckLake extension,
    and attaches the DuckLake database, making it available as a catalog.
    """
    con = ibis.duckdb.connect(extensions=["ducklake"])
    con.attach(f"ducklake:{DUCKLAKE_PATH}", name="vibes")
    con.raw_sql("USE vibes")
    return con


def initialize_metadata():
    """
    Ensures that the internal metadata table for tracking experiments exists.
    This is idempotent and safe to call on every application startup.
    """
    con = get_db_connection()
    if "_vibes_experiments_metadata" in con.list_tables():
        return

    schema = ibis.schema(
        [
            ("name", "string"),
            ("type", "string"),
            ("display_name", "string"),
            ("status", "string"),
            ("created_at", "timestamp"),
        ]
    )
    con.create_table("_vibes_experiments_metadata", schema=schema)

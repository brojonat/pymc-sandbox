"""Database connection and schema management."""

from pymc_vibes.db import get_db_connection_from_env


def verify_db_initialized():
    """
    Ensures that the internal metadata table for tracking experiments exists.
    If the table does not exist, this function will raise an error.
    """
    con = get_db_connection_from_env()
    if "_vibes_experiments_metadata" not in con.list_tables():
        raise RuntimeError(
            "'_vibes_experiments_metadata' table not found. "
            "Please run 'vibes db init' to initialize the database."
        )

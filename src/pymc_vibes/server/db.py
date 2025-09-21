"""Database connection and schema management."""

import os

import ibis

# In a real application, this would come from a config file.
DUCKLAKE_PATH = "pymc-vibes.ducklake"


def get_db_connection():
    """
    Returns an Ibis connection to the DuckLake database.

    This function connects to DuckDB using a PostgreSQL backend for metadata
    and an S3-compatible object store for data, configured via environment
    variables.
    """
    conn = ibis.duckdb.connect()

    # Install necessary extensions
    conn.con.execute("INSTALL httpfs;")
    conn.con.execute("LOAD httpfs;")
    conn.con.execute("INSTALL postgres;")
    conn.con.execute("LOAD postgres;")

    # Get connection params from environment variables with defaults for local dev
    ducklake_name = os.getenv("DUCKLAKE_NAME", "pymc_vibes_ducklake")
    pg_host = os.getenv("PG_HOST", "postgres")
    pg_port = os.getenv("PG_PORT", "5432")
    pg_dbname = os.getenv("PG_DBNAME", "ducklake_catalog")
    pg_user = os.getenv("PG_USER", "user")
    pg_password = os.getenv("PG_PASSWORD", "password")
    s3_data_path = os.getenv("S3_DATA_PATH", "s3://ducklake")
    s3_secret_name = os.getenv("S3_SECRET_NAME", "minio_secret")
    s3_key_id = os.getenv("S3_KEY_ID", "minioadmin")
    s3_secret = os.getenv("S3_SECRET", "minioadmin")
    s3_endpoint = os.getenv("S3_ENDPOINT", "minio:9000")
    s3_url_style = os.getenv("S3_URL_STYLE", "path")
    s3_use_ssl = os.getenv("S3_USE_SSL", "False").lower() in ("true", "1", "t")

    # Configure S3/MinIO access
    conn.con.execute(
        f"""
        CREATE OR REPLACE SECRET {s3_secret_name} (
            TYPE S3,
            KEY_ID '{s3_key_id}',
            SECRET '{s3_secret}',
            ENDPOINT '{s3_endpoint}',
            URL_STYLE '{s3_url_style}',
            USE_SSL {str(s3_use_ssl).lower()}
        );
    """
    )

    # Attach DuckLake
    conn.con.execute(
        f"""
        ATTACH 'ducklake:postgres:dbname={pg_dbname} user={pg_user} password={pg_password} host={pg_host} port={pg_port}' AS {ducklake_name}
            (DATA_PATH '{s3_data_path}');
    """
    )
    conn.con.execute(f"USE {ducklake_name}")
    return conn


def verify_db_initialized():
    """
    Ensures that the internal metadata table for tracking experiments exists.
    If the table does not exist, this function will raise an error.
    """
    con = get_db_connection()
    if "_vibes_experiments_metadata" not in con.list_tables():
        raise RuntimeError(
            "'_vibes_experiments_metadata' table not found. "
            "Please run 'vibes db init' to initialize the database."
        )

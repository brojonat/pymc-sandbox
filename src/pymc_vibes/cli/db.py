"""Migrations subcommand for the CLI."""

import json
from pathlib import Path

import click
import ibis

from pymc_vibes.db import connect_to_ducklake

# Database connection details (mirroring the server and data modules)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_FILE = DATA_DIR / "poisson-cohorts.db"


@click.group(name="db")
def db_cli():
    """Commands for database schema management."""
    pass


@db_cli.command(name="init")
@click.option("--pg-host", default="localhost", help="Postgres host.")
@click.option("--pg-port", default=5432, help="Postgres port.")
@click.option("--pg-dbname", default="ducklake_catalog", help="Postgres database name.")
@click.option("--pg-user", default="user", help="Postgres user.")
@click.option("--pg-password", default="password", help="Postgres password.")
@click.option(
    "--s3-data-path", default="s3://ducklake", help="S3 data path for DuckLake."
)
@click.option(
    "--s3-secret-name", default="minio_secret", help="S3 secret name for DuckDB."
)
@click.option("--s3-key-id", default="minioadmin", help="S3 access key ID.")
@click.option("--s3-secret", default="minioadmin", help="S3 secret access key.")
@click.option("--s3-endpoint", default="localhost:9000", help="S3 endpoint.")
@click.option("--s3-url-style", default="path", help="S3 URL style.")
@click.option(
    "--s3-use-ssl", is_flag=True, default=False, help="Use SSL for S3 connection."
)
@click.option(
    "--ducklake-name",
    default="pymc_vibes_ducklake",
    help="Name for the DuckLake connection.",
)
def init_db(
    pg_host,
    pg_port,
    pg_dbname,
    pg_user,
    pg_password,
    s3_data_path,
    s3_secret_name,
    s3_key_id,
    s3_secret,
    s3_endpoint,
    s3_url_style,
    s3_use_ssl,
    ducklake_name,
):
    """Initialize the DuckLake database and create the application metadata table."""
    conn = connect_to_ducklake(
        pg_host,
        pg_port,
        pg_dbname,
        pg_user,
        pg_password,
        s3_data_path,
        s3_secret_name,
        s3_key_id,
        s3_secret,
        s3_endpoint,
        s3_url_style,
        s3_use_ssl,
        ducklake_name,
    )

    # Create the initial metadata table
    metadata_schema = ibis.schema(
        [
            ("name", "string"),
            ("type", "string"),
            ("display_name", "string"),
            ("status", "string"),
            ("created_at", "timestamp"),
        ]
    )
    conn.create_table("_vibes_experiments_metadata", schema=metadata_schema)

    # dump the existing schema to stdout
    schema_info = {}
    for table_name in conn.list_tables():
        schema = conn.table(table_name).schema()
        schema_info[table_name] = [
            {
                "column_name": name,
                "column_type": str(dtype),
                "nullable": dtype.nullable,
            }
            for name, dtype in schema.items()
        ]

    click.echo(json.dumps(schema_info, indent=2))


@db_cli.command(name="list-tables")
@click.option("--pg-host", default="localhost", help="Postgres host.")
@click.option("--pg-port", default=5432, help="Postgres port.")
@click.option("--pg-dbname", default="ducklake_catalog", help="Postgres database name.")
@click.option("--pg-user", default="user", help="Postgres user.")
@click.option("--pg-password", default="password", help="Postgres password.")
@click.option(
    "--s3-data-path", default="s3://ducklake", help="S3 data path for DuckLake."
)
@click.option(
    "--s3-secret-name", default="minio_secret", help="S3 secret name for DuckDB."
)
@click.option("--s3-key-id", default="minioadmin", help="S3 access key ID.")
@click.option("--s3-secret", default="minioadmin", help="S3 secret access key.")
@click.option("--s3-endpoint", default="localhost:9000", help="S3 endpoint.")
@click.option("--s3-url-style", default="path", help="S3 URL style.")
@click.option(
    "--s3-use-ssl", is_flag=True, default=False, help="Use SSL for S3 connection."
)
@click.option(
    "--ducklake-name",
    default="pymc_vibes_ducklake",
    help="Name for the DuckLake connection.",
)
def list_tables(
    pg_host,
    pg_port,
    pg_dbname,
    pg_user,
    pg_password,
    s3_data_path,
    s3_secret_name,
    s3_key_id,
    s3_secret,
    s3_endpoint,
    s3_url_style,
    s3_use_ssl,
    ducklake_name,
):
    """List all tables in the DuckLake database."""
    conn = connect_to_ducklake(
        pg_host,
        pg_port,
        pg_dbname,
        pg_user,
        pg_password,
        s3_data_path,
        s3_secret_name,
        s3_key_id,
        s3_secret,
        s3_endpoint,
        s3_url_style,
        s3_use_ssl,
        ducklake_name,
    )
    click.echo(json.dumps(conn.list_tables(), indent=2))


@db_cli.command(name="inspect")
@click.option("--pg-host", default="localhost", help="Postgres host.")
@click.option("--pg-port", default=5432, help="Postgres port.")
@click.option("--pg-dbname", default="ducklake_catalog", help="Postgres database name.")
@click.option("--pg-user", default="user", help="Postgres user.")
@click.option("--pg-password", default="password", help="Postgres password.")
@click.option(
    "--s3-data-path", default="s3://ducklake", help="S3 data path for DuckLake."
)
@click.option(
    "--s3-secret-name", default="minio_secret", help="S3 secret name for DuckDB."
)
@click.option("--s3-key-id", default="minioadmin", help="S3 access key ID.")
@click.option("--s3-secret", default="minioadmin", help="S3 secret access key.")
@click.option("--s3-endpoint", default="localhost:9000", help="S3 endpoint.")
@click.option("--s3-url-style", default="path", help="S3 URL style.")
@click.option(
    "--s3-use-ssl", is_flag=True, default=False, help="Use SSL for S3 connection."
)
@click.option(
    "--ducklake-name",
    default="pymc_vibes_ducklake",
    help="Name for the DuckLake connection.",
)
@click.option("--table-name", required=True, help="Name of the table to inspect.")
def inspect_table(
    pg_host,
    pg_port,
    pg_dbname,
    pg_user,
    pg_password,
    s3_data_path,
    s3_secret_name,
    s3_key_id,
    s3_secret,
    s3_endpoint,
    s3_url_style,
    s3_use_ssl,
    ducklake_name,
    table_name,
):
    """Inspect the schema of a specific table."""
    conn = connect_to_ducklake(
        pg_host,
        pg_port,
        pg_dbname,
        pg_user,
        pg_password,
        s3_data_path,
        s3_secret_name,
        s3_key_id,
        s3_secret,
        s3_endpoint,
        s3_url_style,
        s3_use_ssl,
        ducklake_name,
    )
    if table_name not in conn.list_tables():
        click.echo(
            json.dumps({"error": f"Table '{table_name}' not found."}),
            err=True,
        )
        return

    table = conn.table(table_name)
    schema = table.schema()
    row_count = table.count().execute()

    schema_info = [
        {
            "column_name": name,
            "column_type": str(dtype),
            "nullable": dtype.nullable,
        }
        for name, dtype in schema.items()
    ]
    output = {
        "table_name": table_name,
        "row_count": int(row_count),
        "schema": schema_info,
    }
    click.echo(json.dumps(output, indent=2))


@db_cli.command(name="drop-table")
@click.option("--pg-host", default="localhost", help="Postgres host.")
@click.option("--pg-port", default=5432, help="Postgres port.")
@click.option("--pg-dbname", default="ducklake_catalog", help="Postgres database name.")
@click.option("--pg-user", default="user", help="Postgres user.")
@click.option("--pg-password", default="password", help="Postgres password.")
@click.option(
    "--s3-data-path", default="s3://ducklake", help="S3 data path for DuckLake."
)
@click.option(
    "--s3-secret-name", default="minio_secret", help="S3 secret name for DuckDB."
)
@click.option("--s3-key-id", default="minioadmin", help="S3 access key ID.")
@click.option("--s3-secret", default="minioadmin", help="S3 secret access key.")
@click.option("--s3-endpoint", default="localhost:9000", help="S3 endpoint.")
@click.option("--s3-url-style", default="path", help="S3 URL style.")
@click.option(
    "--s3-use-ssl", is_flag=True, default=False, help="Use SSL for S3 connection."
)
@click.option(
    "--ducklake-name",
    default="pymc_vibes_ducklake",
    help="Name for the DuckLake connection.",
)
@click.option("--table-name", required=True, help="Name of the table to drop.")
def drop_table(
    pg_host,
    pg_port,
    pg_dbname,
    pg_user,
    pg_password,
    s3_data_path,
    s3_secret_name,
    s3_key_id,
    s3_secret,
    s3_endpoint,
    s3_url_style,
    s3_use_ssl,
    table_name,
    ducklake_name,
):
    """Drop a table from the DuckLake database."""
    conn = connect_to_ducklake(
        pg_host,
        pg_port,
        pg_dbname,
        pg_user,
        pg_password,
        s3_data_path,
        s3_secret_name,
        s3_key_id,
        s3_secret,
        s3_endpoint,
        s3_url_style,
        s3_use_ssl,
        ducklake_name,
    )
    conn.con.execute(f"DROP TABLE IF EXISTS {table_name};")
    click.echo(json.dumps(conn.list_tables(), indent=2))

"""CLI commands for database migrations."""

import click

from pymc_vibes.db import connect_to_ducklake


@click.group("migrations")
def migrations_cli():
    """Run database migrations."""
    pass


@migrations_cli.command("rename-bernoulli-conversion-to-outcome")
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
def rename_bernoulli_conversion_to_outcome(
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
    """
    Rename the 'conversion' column to 'outcome' in all Bernoulli experiments.

    This is a compatibility migration to align older experiment data with
    updates to the frontend and data generation scripts.

    This is a pretty hacky migration but it's a good demonstration of how to
    implement ad-hoc migrations if you're really in a pinch need to make schema changes
    across multiple experiments.

    """
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

    # 1. Find all Bernoulli experiments from the metadata table
    try:
        metadata = conn.table("_vibes_experiments_metadata")
        bernoulli_experiments = metadata.filter(metadata.type == "bernoulli").execute()
    except Exception as e:
        click.echo(
            f"Error: Could not query experiment metadata. Is the database initialized? ({e})",
            err=True,
        )
        return

    if bernoulli_experiments.empty:
        click.echo("No Bernoulli experiments found to migrate.", err=True)
        return

    click.echo(
        f"Found {len(bernoulli_experiments)} Bernoulli experiments. Checking for migration...",
        err=True,
    )

    # 2. For each experiment, check for 'conversion' column and rename if present
    migrated_count = 0
    for experiment in bernoulli_experiments.to_dict("records"):
        exp_name = experiment["name"]
        try:
            table = conn.table(exp_name)
            if "conversion" in table.columns and "outcome" not in table.columns:
                click.echo(f"  -> Migrating '{exp_name}'...", err=True)
                conn.con.execute(
                    f'ALTER TABLE "{exp_name}" RENAME COLUMN conversion TO outcome;'
                )
                migrated_count += 1
            else:
                click.echo(
                    f"  -> Skipping '{exp_name}', no 'conversion' column found.",
                    err=True,
                )
        except Exception as e:
            click.echo(f"  -> Error processing experiment '{exp_name}': {e}", err=True)

    click.echo(
        f"\nMigration complete. {migrated_count} experiment(s) were successfully migrated.",
        err=True,
    )

"""data.py"""

import click
import ibis


# this should be a subcommand of the db cli
@click.group(name="data")
def data_cli():
    """Commands for data operations."""


@data_cli.command(name="inspect")
@click.option("--infile", type=click.Path(exists=True), required=True)
def load_data(infile):
    """Inspect the data."""
    ibis.read_parquet(infile)

# ruff: noqa: E402
"""Main CLI command group."""

import warnings

# Suppress the Numba FNV hashing warning, which is not relevant to our use case.
# This must be done before any pymc/numba imports happen.
warnings.filterwarnings(
    "ignore",
    message=".*FNV hashing is not implemented in Numba.*",
    category=UserWarning,
    module="numba.cpython.hashing",
)

import click

from pymc_vibes.cli.data import data_cli
from pymc_vibes.cli.db import db_cli
from pymc_vibes.cli.experiments import experiments_cli
from pymc_vibes.cli.generate import generate_cli
from pymc_vibes.cli.migrations import migrations_cli

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    """pymc-vibes command line interface."""
    pass


cli.add_command(db_cli)
cli.add_command(data_cli)
cli.add_command(experiments_cli)
cli.add_command(generate_cli)
cli.add_command(migrations_cli)


def main():
    """CLI entrypoint."""
    cli()


if __name__ == "__main__":
    main()

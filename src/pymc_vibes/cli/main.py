"""Main CLI command group."""

import click

from pymc_vibes.cli.events import events_cli
from pymc_vibes.cli.experiments import experiments_cli
from pymc_vibes.cli.generate import generate_cli

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    """pymc-vibes command line interface."""
    pass


cli.add_command(experiments_cli)
cli.add_command(events_cli)
cli.add_command(generate_cli)


def main():
    """CLI entrypoint."""
    cli()


if __name__ == "__main__":
    main()

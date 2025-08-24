"""cli.py"""

import click

from .data import data
from .migrations import migrations

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=CONTEXT_SETTINGS)
def cli() -> None:
    """pymc-vibes command line interface."""
    pass


@cli.command()
@click.option("--name", "-n", default="world", help="Who to greet.")
def hello(name: str) -> None:
    """Example subcommand to verify installation and CLI plumbing."""
    click.echo(f"Hello, {name}!")


cli.add_command(data)
cli.add_command(migrations)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()

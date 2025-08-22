"""cli.py"""

import click

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=CONTEXT_SETTINGS)
def cli() -> None:
    """pymc-llm-dev command line interface."""
    pass


@cli.command()
@click.option("--name", "-n", default="world", help="Who to greet.")
def hello(name: str) -> None:
    """Example subcommand to verify installation and CLI plumbing."""
    click.echo(f"Hello, {name}!")


def main() -> None:
    """Entrypoint that invokes the Click CLI group."""
    cli()


if __name__ == "__main__":
    main()

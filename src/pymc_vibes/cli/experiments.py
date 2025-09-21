"""CLI commands for managing experiments."""

import json

import click
import httpx

from pymc_vibes.cli.client import APIClient


@click.group("experiments")
def experiments_cli():
    """Create, read, update, delete, and list experiments."""
    pass


@experiments_cli.command("list")
def list_experiments():
    """List all experiments as JSON."""
    client = APIClient()
    try:
        response = client.list_experiments()
        click.echo(json.dumps(response.json(), indent=2))
    except httpx.HTTPStatusError as e:
        error_details = e.response.json()
        click.echo(json.dumps(error_details, indent=2), err=True)
    except httpx.RequestError as e:
        error_message = {"error": "Failed to connect to API", "details": str(e)}
        click.echo(json.dumps(error_message, indent=2), err=True)


@experiments_cli.command("create")
@click.argument("experiment_name")
@click.option(
    "--display-name", required=True, help="A user-friendly name for the experiment."
)
@click.option(
    "--type",
    "experiment_type",
    required=True,
    type=click.Choice(
        ["ab-test", "bernoulli", "multi-armed-bandits", "poisson-cohorts"],
        case_sensitive=False,
    ),
    help="The type of the experiment.",
)
@click.argument("initial_data_file", type=click.Path(exists=True, dir_okay=False))
def create_experiment(
    experiment_name: str,
    display_name: str,
    experiment_type: str,
    initial_data_file: str,
):
    """Create a new experiment from an initial data file."""
    client = APIClient()
    try:
        response = client.create_experiment(
            experiment_name, experiment_type, display_name, initial_data_file
        )
        click.echo(json.dumps(response.json(), indent=2))
    except httpx.HTTPStatusError as e:
        error_details = e.response.json()
        click.echo(json.dumps(error_details, indent=2), err=True)
    except httpx.RequestError as e:
        error_message = {"error": "Failed to connect to API", "details": str(e)}
        click.echo(json.dumps(error_message, indent=2), err=True)
    except FileNotFoundError:
        error_message = {"error": "File not found", "details": initial_data_file}
        click.echo(json.dumps(error_message, indent=2), err=True)


@experiments_cli.command("delete")
@click.argument("experiment_name")
def delete_experiment(experiment_name: str):
    """Delete an experiment and its associated data."""
    client = APIClient()
    try:
        client.delete_experiment(experiment_name)
        # On success, list the remaining experiments to confirm the new state
        response = client.list_experiments()
        click.echo(json.dumps(response.json(), indent=2))
    except httpx.HTTPStatusError as e:
        # If the delete failed, it might be because the experiment was already gone (404)
        # Or it could be another server error.
        error_details = e.response.json()
        click.echo(json.dumps(error_details, indent=2), err=True)
    except httpx.RequestError as e:
        error_message = {"error": "Failed to connect to API", "details": str(e)}
        click.echo(json.dumps(error_message, indent=2), err=True)

"""CLI commands for managing experiments."""

import json
from datetime import datetime
from typing import Optional

import click
import httpx

from pymc_vibes.cli.cli_types import Timestamp
from pymc_vibes.cli.client import APIClient


@click.group("experiments")
def experiments_cli():
    """Create, list, and delete experiments."""
    pass


@experiments_cli.command("list")
def list_experiments():
    """List all experiments as JSON."""
    client = APIClient()
    try:
        response = client.list_experiments()
        click.echo(json.dumps(response.json(), indent=2))
    except httpx.HTTPStatusError as e:
        try:
            error_details = e.response.json()
            click.echo(json.dumps(error_details, indent=2), err=True)
        except json.JSONDecodeError:
            error_message = {
                "error": "Failed to decode server error response",
                "status_code": e.response.status_code,
                "response_text": e.response.text,
            }
            click.echo(json.dumps(error_message, indent=2), err=True)
    except httpx.RequestError as e:
        error_message = {"error": "Failed to connect to API", "details": str(e)}
        click.echo(json.dumps(error_message, indent=2), err=True)


@experiments_cli.command("create")
@click.option(
    "--experiment-name", required=True, help="A unique name for the experiment."
)
@click.option("--display-name", help="A user-friendly name for the experiment.")
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
@click.option(
    "--initial-data-file",
    default="-",
    type=click.File("r"),
    help="Path to the initial JSON data file. Defaults to stdin.",
)
def create_experiment(
    experiment_name: str,
    display_name: str,
    experiment_type: str,
    initial_data_file: str,
):
    """Create a new experiment from an initial data file."""
    if not display_name:
        display_name = experiment_name
    client = APIClient()
    try:
        response = client.create_experiment(
            experiment_name, experiment_type, display_name, initial_data_file
        )
        click.echo(json.dumps(response.json(), indent=2))
    except httpx.HTTPStatusError as e:
        try:
            error_details = e.response.json()
            click.echo(json.dumps(error_details, indent=2), err=True)
        except json.JSONDecodeError:
            error_message = {
                "error": "Failed to decode server error response",
                "status_code": e.response.status_code,
                "response_text": e.response.text,
            }
            click.echo(json.dumps(error_message, indent=2), err=True)
    except httpx.RequestError as e:
        error_message = {"error": "Failed to connect to API", "details": str(e)}
        click.echo(json.dumps(error_message, indent=2), err=True)


@experiments_cli.command("inspect")
@click.option(
    "--experiment-name", required=True, help="The name of the experiment to inspect."
)
@click.option(
    "--start",
    type=Timestamp(),
    help="Start timestamp (Unix, YYYY-MM-DDTHH:MM:SS, YYYY-MM-DD, or YYYYMMDD).",
)
@click.option(
    "--end",
    type=Timestamp(),
    help="End timestamp (Unix, YYYY-MM-DDTHH:MM:SS, YYYY-MM-DD, or YYYYMMDD).",
)
@click.option("--limit", type=int, default=100, help="Number of rows to return.")
@click.option("--offset", type=int, default=0, help="Number of rows to skip.")
def inspect_experiment(
    experiment_name: str,
    start: Optional[datetime],
    end: Optional[datetime],
    limit: int,
    offset: int,
):
    """Inspect the data for a single experiment."""
    client = APIClient()
    try:
        start_iso = start.isoformat() if start else None
        end_iso = end.isoformat() if end else None
        response = client.inspect_experiment(
            experiment_name, start_iso, end_iso, limit, offset
        )
        click.echo(json.dumps(response.json(), indent=2))
    except httpx.HTTPStatusError as e:
        try:
            error_details = e.response.json()
            click.echo(json.dumps(error_details, indent=2), err=True)
        except json.JSONDecodeError:
            error_message = {
                "error": "Failed to decode server error response",
                "status_code": e.response.status_code,
                "response_text": e.response.text,
            }
            click.echo(json.dumps(error_message, indent=2), err=True)
    except httpx.RequestError as e:
        error_message = {"error": "Failed to connect to API", "details": str(e)}
        click.echo(json.dumps(error_message, indent=2), err=True)


@experiments_cli.command("delete")
@click.option(
    "--experiment-name", required=True, help="The name of the experiment to delete."
)
def delete_experiment(experiment_name: str):
    """Delete an experiment and its associated data."""
    client = APIClient()
    try:
        client.delete_experiment(experiment_name)
        # On success, list the remaining experiments to confirm the new state
        response = client.list_experiments()
        click.echo(json.dumps(response.json(), indent=2))
    except httpx.HTTPStatusError as e:
        try:
            error_details = e.response.json()
            click.echo(json.dumps(error_details, indent=2), err=True)
        except json.JSONDecodeError:
            error_message = {
                "error": "Failed to decode server error response",
                "status_code": e.response.status_code,
                "response_text": e.response.text,
            }
            click.echo(json.dumps(error_message, indent=2), err=True)
    except httpx.RequestError as e:
        error_message = {"error": "Failed to connect to API", "details": str(e)}
        click.echo(json.dumps(error_message, indent=2), err=True)


@experiments_cli.command("delete-by-type")
@click.option(
    "--type",
    "experiment_type",
    required=True,
    type=click.Choice(
        ["ab-test", "bernoulli", "multi-armed-bandits", "poisson-cohorts"],
        case_sensitive=False,
    ),
    help="The type of the experiments to delete.",
)
def delete_experiments_by_type(experiment_type: str):
    """Delete all experiments of a specific type."""
    client = APIClient()
    try:
        # 1. Fetch all experiments
        response = client.list_experiments()
        all_experiments = response.json().get("experiments", [])

        # 2. Filter for the target type
        to_delete = [
            exp for exp in all_experiments if exp.get("type") == experiment_type
        ]

        if not to_delete:
            click.echo(f"No experiments of type '{experiment_type}' found.", err=True)
            return

        # 3. Delete each one
        click.echo(
            f"Found {len(to_delete)} experiments of type '{experiment_type}' to delete:",
            err=True,
        )
        for exp in to_delete:
            exp_name = exp.get("name")
            if exp_name:
                click.echo(f" - Deleting {exp_name}...", err=True)
                client.delete_experiment(exp_name)

        click.echo("Deletion complete.", err=True)

    except httpx.HTTPStatusError as e:
        try:
            error_details = e.response.json()
            click.echo(json.dumps(error_details, indent=2), err=True)
        except json.JSONDecodeError:
            error_message = {
                "error": "Failed to decode server error response",
                "status_code": e.response.status_code,
                "response_text": e.response.text,
            }
            click.echo(json.dumps(error_message, indent=2), err=True)
    except httpx.RequestError as e:
        error_message = {"error": "Failed to connect to API", "details": str(e)}
        click.echo(json.dumps(error_message, indent=2), err=True)

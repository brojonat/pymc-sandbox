"""CLI commands for managing events."""

import json
import sys

import click
import httpx

from pymc_vibes.cli.client import APIClient


@click.group("events")
def events_cli():
    """Upload and manage event data."""
    pass


@events_cli.command("upload")
@click.option(
    "--experiment-id", required=True, help="The ID of the experiment to upload data to."
)
@click.argument("event_data", type=click.File("r"), default=sys.stdin)
def upload_events(experiment_id: str, event_data):
    """
    Upload a batch of events from a file or stdin to an experiment.

    EVENT_DATA should be a JSON array of event objects.
    """
    try:
        data = json.load(event_data)
        if not isinstance(data, list):
            raise ValueError("Input must be a JSON array of event objects.")
    except (json.JSONDecodeError, ValueError) as e:
        error_message = {"error": "Invalid event data provided", "details": str(e)}
        click.echo(json.dumps(error_message, indent=2), err=True)
        return

    client = APIClient()
    try:
        response = client.upload_events(experiment_id, data)
        click.echo(json.dumps(response.json(), indent=2))
    except httpx.HTTPStatusError as e:
        # Handle HTTP errors (e.g., 404 Not Found, 400 Bad Request)
        try:
            error_details = e.response.json()
        except json.JSONDecodeError:
            error_details = {"error": "Unknown API error", "details": e.response.text}
        click.echo(json.dumps(error_details, indent=2), err=True)
    except httpx.RequestError as e:
        # Handle network errors (e.g., connection refused)
        error_message = {"error": "Failed to connect to API", "details": str(e)}
        click.echo(json.dumps(error_message, indent=2), err=True)

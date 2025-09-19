"""A simple client for interacting with the pymc-vibes API."""

import os
from typing import Any, Dict, List

import httpx

# The base URL can be configured via an environment variable
API_BASE_URL = os.getenv("PYMC_VIBES_API_URL", "http://127.0.0.1:8000")


class APIClient:
    """A client for making requests to the pymc-vibes API."""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.client = httpx.Client(base_url=self.base_url)

    def list_experiments(self) -> httpx.Response:
        """Lists all experiments from the API."""
        response = self.client.get("/experiments/")
        response.raise_for_status()
        return response

    def create_experiment(
        self,
        experiment_name: str,
        experiment_type: str,
        display_name: str,
        data_filepath: str,
    ) -> httpx.Response:
        """Creates a new experiment by uploading an initial data file."""
        with open(data_filepath, "rb") as f:
            files = {
                "initial_data": (
                    os.path.basename(data_filepath),
                    f,
                    "application/json",
                )
            }
            data = {
                "experiment_name": experiment_name,
                "experiment_type": experiment_type,
                "display_name": display_name,
            }
            response = self.client.post("/experiments/", files=files, data=data)
        response.raise_for_status()
        return response

    def delete_experiment(self, experiment_name: str) -> httpx.Response:
        """Deletes an experiment via the API."""
        url = f"/experiments/{experiment_name}"
        response = self.client.delete(url)
        response.raise_for_status()
        return response

    def upload_events(
        self, experiment_name: str, events: List[Dict[str, Any]]
    ) -> httpx.Response:
        """
        Uploads a batch of events to a specific experiment.

        :param experiment_name: The name of the experiment (table).
        :param events: A list of event dictionaries to upload.
        :return: The response from the API.
        """
        url = f"/events/{experiment_name}"
        response = self.client.post(url, json=events)
        response.raise_for_status()  # Raise an exception for 4xx/5xx responses
        return response

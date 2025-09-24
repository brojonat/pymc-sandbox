"""CLI API client for interacting with the pymc-vibes server."""

import json
import os
from typing import IO, Any, Dict, List, Optional

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
        response = self.client.get("/experiments")
        response.raise_for_status()
        return response

    def create_experiment(
        self,
        experiment_name: str,
        experiment_type: str,
        display_name: str,
        data_file: IO,
    ) -> httpx.Response:
        """Creates a new experiment by uploading an initial data file."""
        initial_data = json.load(data_file)

        payload = {
            "experiment_name": experiment_name,
            "experiment_type": experiment_type,
            "display_name": display_name,
            "initial_data": initial_data,
        }
        response = self.client.post("/experiments", json=payload)
        response.raise_for_status()
        return response

    def inspect_experiment(
        self,
        experiment_name: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> httpx.Response:
        """Inspects data for a single experiment."""
        url = "/experiments/data"
        params = {"experiment_name": experiment_name, "limit": limit, "offset": offset}
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response

    def delete_experiment(self, experiment_name: str) -> httpx.Response:
        """Deletes an experiment via the API."""
        url = "/experiments"
        params = {"experiment_name": experiment_name}
        response = self.client.delete(url, params=params)
        response.raise_for_status()
        return response

    def upload_events(
        self, experiment_name: str, events: List[Dict[str, Any]]
    ) -> httpx.Response:
        """Uploads a batch of events to a specific experiment."""
        url = "/events"
        params = {"experiment_name": experiment_name}
        response = self.client.post(url, params=params, json=events)
        response.raise_for_status()
        return response

    def list_cache(self, experiment_name: str) -> httpx.Response:
        """Lists all cached MLflow runs for an experiment."""
        url = "/experiments/list-cache"
        params = {"experiment_name": experiment_name}
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response

    def clear_cache(self, experiment_name: str) -> httpx.Response:
        """Clears the MLflow cache for an experiment."""
        url = "/experiments/clear-cache"
        params = {"experiment_name": experiment_name}
        response = self.client.post(url, params=params)
        response.raise_for_status()
        return response

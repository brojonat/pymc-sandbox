"""MLflow client setup and dependency injection."""

import os
from typing import Optional

import mlflow
from mlflow.tracking import MlflowClient

mlflow_client: Optional[MlflowClient] = None


def init_mlflow_client():
    """Initializes the MLflow client singleton."""
    global mlflow_client
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow_client = MlflowClient(tracking_uri=tracking_uri)


def get_mlflow_client() -> MlflowClient:
    """FastAPI dependency that provides the singleton MLflow client."""
    return mlflow_client

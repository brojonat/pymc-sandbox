"""
This module provides a caching mechanism for PyMC InferenceData objects using MLflow.
It is designed to be used within a FastAPI application where an MLflow client
is available via dependency injection.
"""

import hashlib
import os
import tempfile
from typing import Any, Callable

import arviz as az
import pandas as pd
from mlflow.tracking import MlflowClient


def get_or_create_idata(
    experiment_name: str,
    data: pd.DataFrame | pd.Series,
    model_fit_function: Callable[[pd.DataFrame | pd.Series], Any],
    mlflow_client: MlflowClient,
) -> Any:
    """
    Retrieves InferenceData from an MLflow cache or creates, caches, and returns it.

    This function implements a cache-aside pattern for PyMC InferenceData objects.
    It first checks if a run with a matching data hash exists in the specified
    MLflow experiment. If it does, the InferenceData is downloaded from the run's
    artifacts. If not, it executes the provided model fitting function, saves the
    resulting InferenceData as an artifact in a new MLflow run, and then returns it.

    Parameters
    ----------
    experiment_name : str
        The name of the MLflow experiment to use for caching.
    data : pd.DataFrame | pd.Series
        The input data for the model. This data is hashed to create a unique
        cache key.
    model_fit_function : Callable[[pd.DataFrame | pd.Series], Any]
        A callable that takes the data as input and returns a PyMC
        InferenceData object.
    mlflow_client : MlflowClient
        An initialized MLflow Tracking Client.

    Returns
    -------
    Any
        The cached or newly created PyMC InferenceData object.
    """
    bucket_name = os.getenv("MLFLOW_S3_BUCKET_NAME", "mlflow")
    artifact_location = f"s3://{bucket_name}"

    experiment = mlflow_client.get_experiment_by_name(name=experiment_name)
    # If the experiment does not exist or was deleted, create/restore it.
    if experiment is None:
        experiment_id = mlflow_client.create_experiment(
            name=experiment_name, artifact_location=artifact_location
        )
    elif experiment.lifecycle_stage == "deleted":
        mlflow_client.restore_experiment(experiment.experiment_id)
        experiment_id = experiment.experiment_id
    else:
        experiment_id = experiment.experiment_id

    # 1. Create a unique hash from the data and experiment name
    hasher = hashlib.sha256()
    hasher.update(experiment_name.encode())
    data_hash = pd.util.hash_pandas_object(data, index=True).values
    hasher.update(data_hash)
    data_hash = hasher.hexdigest()

    # 2. Search for an existing run
    runs = mlflow_client.search_runs(
        experiment_ids=[experiment_id],
        filter_string=f"tags.data_hash = '{data_hash}'",
        max_results=1,
    )

    if runs:
        # 3. Cache Hit
        run_id = runs[0].info.run_id
        with tempfile.TemporaryDirectory() as tmpdir:
            # Download all artifacts for the run. This is more robust than
            # downloading a single, named artifact file.
            mlflow_client.download_artifacts(run_id, "", tmpdir)
            artifact_path = os.path.join(tmpdir, "idata.nc")
            if not os.path.exists(artifact_path):
                raise FileNotFoundError(
                    f"Could not find 'idata.nc' in the artifacts for run {run_id}. "
                    f"Contents of download dir: {os.listdir(tmpdir)}"
                )
            idata = az.from_netcdf(artifact_path)
            # Load the data into memory before the temporary directory is deleted.
            idata.load()
    else:
        # 4. Cache Miss
        run = mlflow_client.create_run(experiment_id=experiment_id)
        run_id = run.info.run_id
        try:
            mlflow_client.set_tag(run_id, "data_hash", data_hash)
            idata = model_fit_function(data)

            with tempfile.TemporaryDirectory() as tmpdir:
                # Save the InferenceData to a named file within the directory.
                idata_path = os.path.join(tmpdir, "idata.nc")
                idata.to_netcdf(idata_path)
                # Log the single file as an artifact.
                mlflow_client.log_artifact(run_id, idata_path)

        except Exception as e:
            # If any part of the process fails, terminate the run with a FAILED status
            # and delete it to prevent a bad cache hit on subsequent requests.
            mlflow_client.set_terminated(run_id, "FAILED")
            mlflow_client.delete_run(run_id)
            # Re-raise the exception to ensure the original request fails.
            raise e
        finally:
            # Ensure the run is always terminated, even on success.
            if mlflow_client.get_run(run_id).info.lifecycle_stage == "active":
                mlflow_client.set_terminated(run_id, "FINISHED")
    return idata

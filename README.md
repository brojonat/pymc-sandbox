# pymc-vibes

TODO: forward more interesting data from the InferenceData object to the frontend.

`pymc-vibes` is a demonstration project for managing and visualizing data from various statistical experiments, such as A/B tests, Bernoulli trials, and more. It features a FastAPI backend, a web UI for visualizations, and a powerful command-line interface for programmatic control.

The data layer is built on a modern lakehouse architecture using DuckDB and the DuckLake format, with Ibis providing a clean, dataframe-style API.

The project provides a framework for several common statistical use cases, including: modeling simple success/failure outcomes with **Bernoulli trials**, comparing conversion rates in **A/B tests**, solving exploration/exploitation problems with **Multi-Armed Bandits**, and estimating event rates over time for different groups with **Poisson Cohorts**. The goal is to provide a practical, hands-on example of how modern data tools can be combined with powerful libraries like PyMC to solve real-world problems.

## Getting Started

### Prerequisites

- Python 3.8+
- `uv` (or `pip`) for package management

### Installation

1.  **Clone the repository:**

```bash
git clone https://github.com/pymc-labs/pymc-vibes.git
cd pymc-vibes
```

2.  **Set up the local environment:**

This project includes a Docker Compose file to spin up a local Postgres database and a MinIO S3-compatible object store.

```bash
docker-compose up -d
```

You will also need to create a bucket in MinIO for DuckLake to use. You can do this through the MinIO console at [http://localhost:9090](http://localhost:9090). Use `minioadmin` for both the username and password. Create a bucket named `ducklake`.

3.  **Install dependencies:**

```bash
uv pip install -e .
```

4.  **Initialize the Database:**

Before running the server or CLI, you must initialize the database. This creates the necessary internal metadata tables. You will get an error if you try running the server before initializing the DB.

```bash
vibes db init
```

You can verify the test table was created:

```bash
vibes db list-tables
```

You can inspect any table in the DB directly as well:

```bash
vibes db inspect --table-name foo
```

### MLflow Integration for Caching

`pymc-vibes` uses [MLflow](https://mlflow.org/) to cache the results of computationally expensive Bayesian model fitting. When a request is made to a posterior endpoint (e.g., for an A/B test), the server first checks if the exact same request has been processed before by looking for a matching run in MLflow.

- If a cached result is found, it is returned immediately, saving significant time.
- If no cached result is found, the PyMC model is fitted, and the resulting `InferenceData` object is stored as an artifact in a new MLflow run for future use.

This caching mechanism is enabled by default and is transparent to the user.

The server has an endpoint that enables users to clear the cache for a given experiment.

#### MLflow Configuration

To function correctly, the server needs to connect to an MLflow backend store (for tracking metadata) and an artifact store (for storing model results). `pymc-vibes` is configured to use the same RDBMS (e.g., Postgres) and object store (e.g., MinIO) services that power the DuckLake data layer.

NOTE: you will need to create necessary database (e.g., `mlflow`) and bucket (e.g., `mlflow`); that is left as an exercise to the reader.

You must set the following environment variables for the MLflow integration to work:

- `MLFLOW_TRACKING_URI`: The PostgreSQL connection string for the MLflow backend store.
- `MLFLOW_S3_BUCKET_NAME`: The name of the bucket in MinIO to use for the artifact store (e.g., `mlflow`).
- `MLFLOW_S3_ENDPOINT_URL`: The URL for the MinIO server (for the MLflow server).
- `AWS_ACCESS_KEY_ID`: The access key for MinIO (e.g., `minioadmin`).
- `AWS_SECRET_ACCESS_KEY`: The secret key for MinIO (e.g., `minioadmin`).
- `AWS_ENDPOINT_URL`: The URL for the MinIO server (for the S3 client, `boto3`).

When running locally with the provided `docker-compose.yml`, these variables will typically be set to `http://localhost:9000` for the endpoint URLs.

## Running the Server

To start the FastAPI server, run the following command:

```bash
uvicorn pymc_vibes.server.main:app --reload
# or more conveniently, use the make target
make run-server
```

The server will be available at `http://127.0.0.1:8000`. You can access the web UI by navigating to this address in your browser. The API documentation is available at `http://127.0.0.1:8000/docs`.

## Usage: A Complete CLI Workflow

The `vibes` CLI is the primary way to manage experiments and data. The following is a comprehensive walkthrough of a typical workflow.

### Step 1: Generate Initial Data

First, let's generate some dummy data for a new A/B test. The `generate` command can output to a file or `stdout`. We'll save it to a file but in practice you'd just pipe this to your next command.

```bash
vibes generate ab-test --num-events 200 --output initial_data.json
```

### Step 2: Create a New Experiment

Now, we'll use the data file to create our first experiment. The `create` command requires a unique name for the experiment (which will be the table name), a user-friendly display name (optional), the experiment type, and the path to the initial data file (defaults to stdin).

```bash
vibes experiments create ab_test_1 \
    --display-name "Test 1: Homepage Button Color" \
    --type "ab-test" \
    --initial-data-file initial_data.json
```

This command creates a new table named `ab_test_1` in DuckLake with a schema compatible with `ab-test` experiments, populates it with the data from `initial_data.json`, and adds a record to the central metadata table that links the data table to the experiment.

### Step 3: Generate and Upload More Data

Experiments are rarely static. Let's generate more data and upload it to our existing experiment.

First, generate a new batch of data and upload it. Instead of using input/output files, we'll just pipe the data this time:

```bash
vibes generate ab-test --num-events 300 | \
vibes events upload --name ab_test_1
```

### Step 4: Create a Second Experiment

Let's create another experiment, this time for a Bernoulli trial:

```bash
vibes generate bernoulli --num-events 150 | \
vibes experiments create bernoulli_trial_1 \
    --display-name "User Engagement Action" \
    --type "bernoulli"
```

### Step 5: List All Experiments

Now that we have a couple of experiments, we can list them to see their metadata.

```bash
vibes experiments list
```

This command queries the central metadata table and returns a JSON array of all registered experiments.

### Step 6: Get Experiment Schema

Suppose you want to curate data manually for an experiment and then upload it to create a new experiment, but you've forgotten the what the schema looks like for the relevant experiment type. You can programmatically query the schema like this:

```bash
vibes experiments schema --type ab-test
```

### Step 6: Delete an Experiment

Finally, to clean up, you can delete an experiment. This will drop the experiment's data table and remove its record from the metadata table.

```bash
vibes experiments delete ab_test_1
```

This completes a typical lifecycle of creating, updating, and managing experiments via the CLI.

## Alternative Workflow: Interactive Data Preparation

While the CLI is ideal for automated and repeatable tasks, much real-world analysis begins with interactive exploration of messy data. This project includes an example of this workflow in `notebooks/nhtsa-experiments.ipynb`.

This notebook-driven approach combines the flexibility of interactive data science tools with the robust experiment management of the `vibes` CLI.

The workflow is as follows:

1.  **Explore and Clean:** A large, raw dataset (in this case, from the NHTSA) is loaded, cleaned, and transformed using [Ibis](https://ibis-project.org/) in a Jupyter notebook. This is where you can handle missing data, parse complex columns, and get a feel for the dataset.

2.  **Define and Filter:** You can interactively define a specific cohort for your experiment by changing filter parameters in the notebook. The output filename is generated dynamically based on these filters, ensuring your experiments are easy to track.

```python
# 1. Define filters for a specific experimental cohort
filters = {
    "MAKETXT": "HYUNDAI",
    "MODELTXT": "ELANTRA",
    "YEARTXT": 2010,
}

# 2. Construct the filename and run the data pipeline
fname = create_filename(filters)
# ... ibis pipeline runs here ...
```

3.  **Create Experiment via CLI:** Once the data is prepared and saved to a file, the notebook uses the `!` shell syntax to call the `vibes` CLI, creating a formal experiment from the cleaned data.

```python
# 3. "Dogfood" the CLI to create the experiment
experiment_name = fpath.stem
!vibes experiments create --name {experiment_name} --type poisson-cohorts --initial-data-file {fname}
```

This "best of both worlds" approach allows you to iterate rapidly in a rich, interactive environment while still using your production CLI to formally manage and "dogfood" the experimental data.

This is particularly useful when you really need to wrangle some data to get it into the experiment schema. Remember, you can determine the schema required by a particular experiment type using the following:

```bash
vibes experiments schema --type poisson-cohorts
```

## Development

### Adding an Experiment Type

Adding a new experiment type to `pymc-vibes` involves changes to both the server and the CLI. Here is a step-by-step guide. Let's assume you're adding a new experiment type called `"my-experiment"` designed for a regression analysis to infer customer lifetime value. The schema for this experiment will be 5 feature columns (`x_{i} for i in range(5)`), and a target variable `y` that represents some quantity we'd like to infer.

#### 1. Server-Side Changes

The server needs to be aware of the new experiment's data schema and provide endpoints for its statistical model.

**a. Define the Data Schema**

In `src/pymc_vibes/server/routers/experiments.py`, add the schema for your new experiment to the `EXPERIMENT_SCHEMAS` dictionary. Think carefully about the schema of your experiment data before implementing it here.

```python
# src/pymc_vibes/server/routers/experiments.py

EXPERIMENT_SCHEMAS = {
    # ... existing schemas ...
    "my-experiment": pa.schema(
        [
            pa.field("x_1", pa.float64()),
            pa.field("x_2", pa.float64()),
            pa.field("x_3", pa.float64()),
            pa.field("x_4", pa.float64()),
            pa.field("x_5", pa.float64()),
            pa.field("y", pa.float64()),
        ]
    ),
}
```

**b. Create the PyMC Model and Posterior Routes**

This is the core statistical component.

1.  **Implement the PyMC Model:** Create a new file, `src/pymc_vibes/pymc_models/my_experiment.py`. In this file, define a function (e.g., `fit_my_model`) that takes in data, defines a PyMC model, fits it, and returns an `arviz.InferenceData` object. This file should also contain a data generation function (e.g., `generate_my_data`) for testing and CLI integration. You can use `src/pymc_vibes/pymc_models/poisson.py` as a template.

2.  **Create the Posterior Endpoint:** Create a new router file, `src/pymc_vibes/server/routers/my_experiment.py`. This router will define the API endpoint (e.g., `/my-experiment/posterior`) that end users will call. This endpoint should:
    - Query the data for a given experiment from DuckLake.
    - Call your `fit_my_model` function to run the analysis.
    - Process the resulting `InferenceData` and return a JSON summary.

**c. Mount the New Router**

In `src/pymc_vibes/server/main.py`, import and include your new router in the main FastAPI app.

```python
# src/pymc_vibes/server/main.py

from pymc_vibes.server.routers import (
    # ... existing routers ...
    my_experiment,
)

# ...

app.include_router(my_experiment.router)
```

**d. Add the UI Views**

To make your experiment visible in the web UI, you'll need to:

1.  Add a new route to `src/pymc_vibes/server/routers/ui.py` to handle requests for your experiment type.
2.  Create a corresponding HTML template (e.g., `my_experiment.html`) in `src/pymc_vibes/server/templates/`.

#### 2. CLI-Side Changes

The `vibes` CLI needs to be updated to recognize and handle the new experiment type.

**a. Update Experiment Commands**

In `src/pymc_vibes/cli/cli_types.py`, add `"my-experiment"` to the `SUPPORTED_EXPERIMENTS` list. This is the single source of truth for all CLI commands.

```python
# src/pymc_vibes/cli/cli_types.py

SUPPORTED_EXPERIMENTS = [
    "ab-test",
    "bernoulli",
    "multi-armed-bandits",
    "poisson-cohorts",
    "my-experiment", # Add your new type here
]
```

No other CLI code changes are needed. The commands in `src/pymc_vibes/cli/experiments.py` use a custom `ExperimentType` that reads from this list, so they will automatically support the new type.

**b. Add a Data Generator (Optional)**

To make testing and demonstration easier, add a new data generation command to `src/pymc_vibes/cli/generate.py`. This command should call the data generation function you created in `src/pymc_vibes/pymc_models/my_experiment.py`.

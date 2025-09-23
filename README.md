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
    initial_data.json
```

This command creates a new table named `ab_test_1` in DuckLake, populates it with the data from `initial_data.json`, and adds a record to the central metadata table.

### Step 3: Generate and Upload More Data

Experiments are rarely static. Let's generate more data and upload it to our existing experiment.

First, generate a new batch of data:

```bash
vibes generate ab-test --num-events 300 --output new_events.json
```

Next, use the `events upload` command to append this data to the `ab_test_1` table:

```bash
vibes events upload ab_test_1 new_events.json
```

### Step 4: Create a Second Experiment

Let's create another experiment, this time for a Bernoulli trial. We can generate the data and pipe it directly to the `create` command without saving it to a file first.

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

### Step 6: Delete an Experiment

Finally, to clean up, you can delete an experiment. This will drop the experiment's data table and remove its record from the metadata table.

```bash
vibes experiments delete ab_test_1
```

This completes a typical lifecycle of creating, updating, and managing experiments via the CLI.

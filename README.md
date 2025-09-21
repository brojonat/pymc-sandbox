# pymc-vibes

`pymc-vibes` is a demonstration project for managing and visualizing data from various statistical experiments, such as A/B tests, Bernoulli trials, and more. It features a FastAPI backend, a web UI for visualizations, and a powerful command-line interface for programmatic control.

The data layer is built on a modern lakehouse architecture using DuckDB and the DuckLake format, with Ibis providing a clean, dataframe-style API.

The project provides a framework for several common statistical use cases, including: modeling simple success/failure outcomes with **Bernoulli trials**, comparing conversion rates in **A/B tests**, solving exploration/exploitation problems with **Multi-Armed Bandits**, and estimating event rates over time for different groups with **Poisson Cohorts**. The goal is to provide a practical, hands-on example of how modern data tools can be combined with powerful libraries like PyMC to solve real-world problems.

TODO: currently we just have the data layer implemented, we still need to implement the Bayesian inference endpoints which will give us posteriors for each experiment type which we'll then send to the client for visualization. The way this will (probably) work is that we fit the data for an experiment and output the posterior distributions to a

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

    Before running the server or CLI, you must initialize the database. This creates the necessary internal metadata tables.

    ```bash
    vibes db init
    ```

    You can verify the test table was created

    ```bash
    vibes db list-tables
    # inspect output
    vibes db drop-table test_events
    ```

## Running the Server

To start the FastAPI server, run the following command:

```bash
uvicorn pymc_vibes.server.main:app --reload
```

The server will be available at `http://127.0.0.1:8000`. You can access the web UI by navigating to this address in your browser. The API documentation is available at `http://127.0.0.1:8000/docs`.

## Usage: A Complete CLI Workflow

The `vibes` CLI is the primary way to manage experiments and data. The following is a comprehensive walkthrough of a typical workflow.

### Step 1: Generate Initial Data

First, let's generate some dummy data for a new A/B test. The `generate` command can output to a file or `stdout`. We'll save it to a file.

```bash
vibes generate ab-test --num-events 200 --output initial_data.json
```

_Note: The confirmation message is sent to `stderr`, so it won't interfere with the JSON output._

### Step 2: Create a New Experiment

Now, we'll use the data file to create our first experiment. The `create` command requires a unique name for the experiment (which will be the table name), a user-friendly display name, the experiment type, and the path to the initial data file.

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
    --type "bernoulli" \
    -
```

_Note: The `-` at the end of the `create` command tells it to read from `stdin`._

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

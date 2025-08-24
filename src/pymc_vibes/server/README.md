# pymc-vibes Server

This directory contains the FastAPI server for the `pymc-vibes` application. It provides a web API for data ingestion, management, and Bayesian analysis of Poisson cohort data.

The server is built with FastAPI and includes:

- **Observability**: Prometheus metrics at `/metrics` and structured logging.
- **Authentication**: JWT Bearer token authentication for protected routes.
- **Data Interface**: Uses [Ibis](https://ibis-project.org/) for a database-agnostic data layer, currently connected to DuckDB.

## Running the Server

To run the server locally, use the `Makefile` target from the project root:

```bash
make run-server
```

This command uses `uvicorn` to run the application and handles loading of necessary environment variables from the `.env.server` file.

## API Endpoints

### Health and Authentication

- `GET /healthz`: A simple health check endpoint that returns `{"status": "ok"}`.
- `GET /whoami`: An authenticated endpoint that returns the claims of the provided JWT.
- `GET /metrics`: Exposes application metrics in a Prometheus-compatible format.

### Data Management (`/poisson-cohorts`)

- `POST /poisson-cohorts/upload`: Uploads a batch of event data from a JSON payload into the database.
- `GET /poisson-cohorts/list`: Lists events from the database with optional filters for cohort, event type, and time range.
- `DELETE /poisson-cohorts/delete`: Deletes events from the database that match the specified filters.

### Statistical Analysis (Planned)

Endpoints for running Bayesian analysis and retrieving posterior distributions are planned, as detailed in the project's implementation plan.

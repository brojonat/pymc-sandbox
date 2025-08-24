# pymc-vibes CLI

This directory contains the command-line interface for interacting with the `pymc-vibes` application. The CLI is invoked via the `pv` entrypoint, which is configured in `pyproject.toml`.

## Commands

### `pv hello`

An example command to verify that the CLI is installed and working correctly.

### `pv data`

A group of commands for managing event data in the database.

- `pv data upload`: Uploads event data from a specified JSON file into the database.
- `pv data list`: Lists events from the database with optional filters for cohort, event type, and time range.
- `pv data delete`: Deletes events from the database that match the specified filters.

### `pv migrations`

A group of commands for managing the database schema.

- `pv migrations init-db`: Initializes the database file and creates the necessary tables if they don't already exist.

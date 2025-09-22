#!/usr/bin/env bash

# Set the shell for make explicitly
SHELL := /bin/bash

define setup_env
        $(eval ENV_FILE := $(1))
        $(eval include $(1))
        $(eval export)
endef

help:
	@echo "Available targets:"
	@awk -F ':.*?## ' '/^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort


run-server: ## Run the FastAPI server
	$(call setup_env, .env.server)
	uv run uvicorn pymc_vibes.server.main:app --host 0.0.0.0 --port 8000 --reload

run-mlflow-ui: ## Run the MLflow UI server
	$(call setup_env, .env.server)
	@echo "--- Starting MLflow UI with the following configuration ---"
	@echo "Backend Store URI: $(MLFLOW_TRACKING_URI)"
	@echo "Default Artifact Root: s3://$(MLFLOW_S3_BUCKET_NAME)/"
	@echo "S3 Endpoint URL (for client): $(AWS_ENDPOINT_URL)"
	@echo "---------------------------------------------------------"
	mlflow ui \
		--backend-store-uri $(MLFLOW_TRACKING_URI) \
		--default-artifact-root s3://$(MLFLOW_S3_BUCKET_NAME)/ \
		--host 127.0.0.1 \
		--port 5000

start-dev-session: ## Start a tmux dev session with the API server and MLflow UI
	@tmux new-session -d -s pymc-vibes -n mlflow
	@tmux send-keys -t pymc-vibes:mlflow 'make run-mlflow-ui' C-m
	@tmux new-window -t pymc-vibes -n api
	@tmux send-keys -t pymc-vibes:api 'make run-server' C-m
	@echo "Dev session 'pymc-vibes' started."
	@echo "MLflow UI running in window 'mlflow' (port 5000)"
	@echo "API server running in window 'api' (port 8000)"
	@echo "Attach with: tmux attach -t pymc-vibes"

stop-dev-session: ## Stop the tmux dev session
	@tmux kill-session -t pymc-vibes || true
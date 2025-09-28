#!/bin/bash
#
# This script cleans up all existing experiments and recreates a standard set of
# experiments with fresh, correctly-schematized data.
#
# Assumes that the `vibes` CLI is installed and available in the current
# environment.

set -e # Exit immediately if a command exits with a non-zero status.

# --- Step 1: Delete all existing experiments ---
echo "--- Deleting all existing experiments ---"

# Get the list of experiment names. The `jq` command here extracts the 'name'
# field from each object in the 'experiments' array. The -r flag gives raw string
# output without quotes.
EXPERIMENT_NAMES=$(vibes experiments list | jq -r '.experiments[].name')

if [ -z "$EXPERIMENT_NAMES" ]; then
    echo "No experiments found to delete."
else
    for NAME in $EXPERIMENT_NAMES; do
        echo "Deleting experiment: $NAME"
        vibes experiments delete --name "$NAME" > /dev/null
    done
    echo "All old experiments deleted."
fi

echo ""

# --- Step 2: Recreate standard experiments ---
echo "--- Recreating standard experiments ---"

# A/B Test
echo "Creating 'ab-test-1'..."
vibes generate ab-test --variant "treatment-a:0.1" --variant "treatment-b:0.37" | \
    vibes experiments create \
        --name "red-vs-blue" \
        --display-name "A/B Test 1" \
        --type "ab-test"

vibes generate ab-test --variant "treatment-a:0.2" --variant "treatment-b:0.4" --variant "treatment-c:0.8" | \
    vibes experiments create \
        --name "red-vs-blue-green" \
        --type "ab-test"

# Bernoulli
echo "Creating 'bernoulli-1'..."
vibes generate bernoulli | \
    vibes experiments create \
        --name "bernoulli-1" \
        --display-name "Bernoulli 1" \
        --type "bernoulli"

vibes generate bernoulli --prob 0.7 | \
    vibes experiments create \
        --name "bernoulli-2" \
        --type "bernoulli"

# Poisson Cohorts
echo "Creating 'poisson-cohorts-1'..."
vibes generate  poisson-cohorts \
    --rate 'c-1:tire:2.0' --rate 'c-1:brake:1.0' --rate 'c-2:fire:8.0' \
    --start-date 2001-01-05 --days 90 | \
    vibes experiments create \
        --name "poisson-cohorts-1" \
        --display-name "Poisson Cohorts 1" \
        --type "poisson-cohorts"

vibes generate  poisson-cohorts \
    --rate 'c-1:tire:3.0' --rate 'c-1:brake:12.0' \
    --start-date 2005-01-02 --days 90 | \
    vibes experiments create \
        --name "poisson-cohorts-2" \
        --type "poisson-cohorts"

echo ""
echo "--- All experiments recreated successfully ---"
vibes experiments list

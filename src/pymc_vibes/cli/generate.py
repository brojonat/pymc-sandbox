"""CLI commands for generating dummy data."""

import json
import sys
from datetime import datetime, timedelta

import click
import numpy as np


@click.group("generate")
def generate_cli():
    """Generate dummy data for different experiment types."""
    pass


@generate_cli.command("ab-test")
@click.option("--num-events", "-n", default=100, help="Number of events to generate.")
@click.option(
    "--conversion-rate-a",
    default=0.1,
    help="The conversion rate for treatment A.",
)
@click.option(
    "--conversion-rate-b",
    default=0.12,
    help="The conversion rate for treatment B.",
)
@click.option(
    "--output",
    "-o",
    type=click.File("w"),
    default=sys.stdout,
    help="Output file path (defaults to stdout).",
)
def generate_ab_test_data(
    num_events: int,
    conversion_rate_a: float,
    conversion_rate_b: float,
    output,
):
    """Generate dummy data for an A/B test."""
    events = []
    for _ in range(num_events):
        treatment = np.random.choice(["A", "B"])
        conversion_rate = conversion_rate_a if treatment == "A" else conversion_rate_b
        conversion = np.random.rand() < conversion_rate
        events.append(
            {
                "timestamp": datetime.now().isoformat(),
                "treatment": treatment,
                "conversion": bool(conversion),
            }
        )

    json.dump(events, output, indent=2)
    if output is not sys.stdout:
        click.echo(
            f"Successfully generated {num_events} events to {output.name}", err=True
        )


@generate_cli.command("bernoulli")
@click.option("--num-events", "-n", default=100, help="Number of events to generate.")
@click.option("--prob", default=0.5, help="The probability of a successful trial.")
@click.option(
    "--output",
    "-o",
    type=click.File("w"),
    default=sys.stdout,
    help="Output file path (defaults to stdout).",
)
def generate_bernoulli_data(num_events: int, prob: float, output):
    """Generate dummy data for a series of Bernoulli trials."""
    events = []
    for _ in range(num_events):
        conversion = np.random.rand() < prob
        events.append(
            {
                "timestamp": datetime.now().isoformat(),
                "conversion": bool(conversion),
            }
        )

    json.dump(events, output, indent=2)
    if output is not sys.stdout:
        click.echo(
            f"Successfully generated {num_events} events to {output.name}", err=True
        )


@generate_cli.command("multi-armed-bandits")
@click.option("--num-events", "-n", default=500, help="Number of events to generate.")
@click.option(
    "--arm-probs",
    default="0.1,0.12,0.08,0.15",
    help="Comma-separated list of reward probabilities for each arm.",
)
@click.option(
    "--output",
    "-o",
    type=click.File("w"),
    default=sys.stdout,
    help="Output file path (defaults to stdout).",
)
def generate_mab_data(num_events: int, arm_probs: str, output):
    """Generate dummy data for a multi-armed bandit problem."""
    try:
        probs = [float(p) for p in arm_probs.split(",")]
        num_arms = len(probs)
    except ValueError:
        click.echo(
            "Error: --arm-probs must be a comma-separated list of numbers.", err=True
        )
        return

    events = []
    for _ in range(num_events):
        # In a real bandit, the arm choice would be strategic. Here we just sample uniformly.
        arm_choice = np.random.randint(0, num_arms)
        reward_prob = probs[arm_choice]
        reward = np.random.rand() < reward_prob
        events.append(
            {
                "timestamp": datetime.now().isoformat(),
                "arm": arm_choice,
                "reward": 1 if reward else 0,
            }
        )

    json.dump(events, output, indent=2)
    if output is not sys.stdout:
        click.echo(
            f"Successfully generated {num_events} events to {output.name}", err=True
        )


@generate_cli.command("poisson-cohorts")
@click.option("--num-events", "-n", default=1000, help="Number of events to generate.")
@click.option(
    "--cohorts",
    default="campaign-A,campaign-B,organic",
    help="Comma-separated list of cohort names.",
)
@click.option(
    "--event-types",
    default="login,purchase,logout",
    help="Comma-separated list of event types.",
)
@click.option(
    "--days", default=30, help="Number of days over which to generate events."
)
@click.option(
    "--output",
    "-o",
    type=click.File("w"),
    default=sys.stdout,
    help="Output file path (defaults to stdout).",
)
def generate_poisson_data(
    num_events: int, cohorts: str, event_types: str, days: int, output
):
    """Generate dummy data for a Poisson cohort rate problem."""
    cohort_list = cohorts.split(",")
    type_list = event_types.split(",")

    # Assign a random base rate (events per day) to each cohort/type pair
    rates = np.random.uniform(0.1, 5.0, size=(len(cohort_list), len(type_list)))

    # Calculate total rate to simulate the master Poisson process
    total_rate = rates.sum()
    avg_interval = (days * 24 * 60 * 60) / num_events

    events = []
    current_time = datetime.now()
    for _ in range(num_events):
        # Simulate time between events with an exponential distribution
        time_delta_seconds = np.random.exponential(avg_interval)
        current_time += timedelta(seconds=time_delta_seconds)

        # Decide which cohort/type generated this event
        # This is like throwing a dart at a board divided by the relative rates
        rand_val = np.random.uniform(0, total_rate)
        cumulative_rate = 0
        cohort_idx, type_idx = -1, -1
        for i, c in enumerate(cohort_list):
            for j, et in enumerate(type_list):
                cumulative_rate += rates[i, j]
                if rand_val <= cumulative_rate:
                    cohort_idx, type_idx = i, j
                    break
            if cohort_idx != -1:
                break

        events.append(
            {
                "timestamp": current_time.isoformat(),
                "cohort": cohort_list[cohort_idx],
                "event_type": type_list[type_idx],
            }
        )

    json.dump(events, output, indent=2)
    if output is not sys.stdout:
        click.echo(
            f"Successfully generated {num_events} events to {output.name}", err=True
        )

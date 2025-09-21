"""CLI commands for generating dummy data."""

import json
import sys
from datetime import datetime, timedelta

import click
import numpy as np
import pymc as pm


@click.group("generate")
def generate_cli():
    """Generate dummy data for different experiment types."""
    pass


@generate_cli.command("ab-test")
@click.option("--num-events", "-n", default=100, help="Number of events to generate.")
@click.option(
    "--variant",
    "variants",
    multiple=True,
    default=["A:0.1", "B:0.12"],
    help="Variant in name:rate format. Can be specified multiple times.",
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
    variants: tuple[str],
    output,
):
    """Generate dummy data for an A/B test."""
    try:
        variants_dict = {
            name.strip(): float(rate.strip())
            for name, rate in (pair.split(":") for pair in variants)
        }
    except ValueError:
        click.echo(
            "Error: --variant must be in the format 'name:rate'",
            err=True,
        )
        return

    events = []
    variant_names = list(variants_dict.keys())
    for _ in range(num_events):
        variant = np.random.choice(variant_names)
        conversion_rate = variants_dict[variant]
        conversion = np.random.rand() < conversion_rate
        events.append(
            {
                "timestamp": datetime.now().isoformat(),
                "variant": variant,
                "outcome": int(conversion),
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
        outcome = np.random.rand() < prob
        events.append(
            {
                "timestamp": datetime.now().isoformat(),
                "outcome": bool(outcome),
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
    "--rate",
    "rates_str",
    multiple=True,
    default=[
        "campaign-A:login:1.5",
        "campaign-A:purchase:0.5",
        "campaign-B:login:2.0",
        "campaign-B:purchase:0.8",
        "organic:login:5.0",
        "organic:purchase:1.0",
        "organic:logout:4.0",
    ],
    help="Rate in cohort:event_type:rate format. Can be specified multiple times.",
)
@click.option(
    "--start-date",
    type=click.DateTime(),
    default=None,
    help="The start date for the event data generation (ISO 8601 format). "
    "Defaults to the number of --days ago.",
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
    num_events: int,
    rates_str: tuple[str],
    days: int,
    start_date: datetime | None,
    output,
):
    """Generate dummy data for a Poisson cohort rate problem."""
    try:
        parsed_rates = [
            (c.strip(), e.strip(), float(r.strip()))
            for c, e, r in (rate.split(":") for rate in rates_str)
        ]
    except ValueError:
        click.echo(
            "Error: --rate must be in the format 'cohort:event_type:rate'",
            err=True,
        )
        return

    cohort_list = sorted(list(set(c for c, _, _ in parsed_rates)))
    type_list = sorted(list(set(e for _, e, _ in parsed_rates)))

    cohort_map = {name: i for i, name in enumerate(cohort_list)}
    type_map = {name: i for i, name in enumerate(type_list)}

    rates = np.zeros((len(cohort_list), len(type_list)))
    for cohort, event_type, rate in parsed_rates:
        rates[cohort_map[cohort], type_map[event_type]] = rate

    # Calculate total rate to simulate the master Poisson process
    total_rate = rates.sum()
    avg_interval = (days * 24 * 60 * 60) / num_events

    # Generate all event choices at once using a PyMC model
    p = rates.flatten() / total_rate
    with pm.Model():
        choices = pm.Categorical("choices", p=p, size=num_events)
        idata = pm.sample_prior_predictive(samples=1)

    event_choices = idata.prior["choices"].values.flatten()

    events = []
    if start_date:
        current_time = start_date
    else:
        current_time = datetime.now() - timedelta(days=days)
    for i in range(num_events):
        # Simulate time between events with an exponential distribution
        time_delta_seconds = np.random.exponential(avg_interval)
        current_time += timedelta(seconds=time_delta_seconds)

        # Assign the pre-drawn event choice
        cohort_idx, type_idx = np.unravel_index(event_choices[i], rates.shape)

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

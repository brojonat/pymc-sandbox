"""CLI commands for generating dummy data."""

import json
import random
import sys
import time
from datetime import datetime, timedelta

import click
import numpy as np

from pymc_vibes.pymc_models.multi_armed_bandits import generate_mab_events
from pymc_vibes.pymc_models.poisson import generate_poisson_events
from pymc_vibes.pymc_models.weibull import generate_weibull_data


def generate_hump_shaped_hazard_data(
    num_events: int,
    early_failure_proportion: float = 0.3,
    early_alpha: float = 2.5,
    early_beta: float = 50.0,
    robust_alpha: float = 1.2,
    robust_beta: float = 200.0,
    censoring_time: float = 250.0,
):
    """
    Generates survival data with a hump-shaped (unimodal) hazard rate.

    This is achieved by simulating from a mixture of two Weibull distributions:
    1. A smaller group with a lower scale parameter, representing early failures.
    2. A larger group with a higher scale parameter, representing the main population.

    Parameters
    ----------
    num_events : int
        Total number of events to generate.
    early_failure_proportion : float, optional
        The proportion of the population that belongs to the early failure group.
    early_alpha : float, optional
        Shape parameter for the early failure group.
    early_beta : float, optional
        Scale parameter for the early failure group.
    robust_alpha : float, optional
        Shape parameter for the robust (main) group.
    robust_beta : float, optional
        Scale parameter for the robust (main) group.
    censoring_time : float, optional
        The time at which to censor observations.

    Returns
    -------
    pd.DataFrame
        A DataFrame with 'duration' and 'observed' columns.
    """
    num_early = int(num_events * early_failure_proportion)
    num_robust = num_events - num_early

    # Generate data for the early failure group
    early_df = generate_weibull_data(
        num_events=num_early,
        alpha=early_alpha,
        beta=early_beta,
        censoring_time=censoring_time,
    )

    # Generate data for the robust group
    robust_df = generate_weibull_data(
        num_events=num_robust,
        alpha=robust_alpha,
        beta=robust_beta,
        censoring_time=censoring_time,
    )
    # Concatenate the two groups
    import pandas as pd

    return pd.concat([early_df, robust_df], ignore_index=True).sample(frac=1)


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
    "--arm-param",
    "arm_params_str",
    multiple=True,
    default=["A:0.1:5.0", "B:0.12:5.0", "C:0.08:10.0"],
    help="Arm parameters in name:prob:magnitude format. Can be specified multiple times.",
)
@click.option(
    "--output",
    "-o",
    type=click.File("w"),
    default=sys.stdout,
    help="Output file path (defaults to stdout).",
)
def generate_mab_data(num_events: int, arm_params_str: tuple[str], output):
    """Generate dummy data for a MAB with success probability and magnitude."""
    try:
        arm_params = {}
        for param_str in arm_params_str:
            name, prob, magnitude = param_str.split(":")
            arm_params[name.strip()] = {
                "prob": float(prob.strip()),
                "magnitude": float(magnitude.strip()),
            }
    except ValueError:
        click.echo(
            "Error: --arm-param must be in the format 'name:prob:magnitude'",
            err=True,
        )
        return

    df = generate_mab_events(arm_params=arm_params, num_events=num_events)

    df["timestamp"] = [datetime.now().isoformat() for _ in range(num_events)]

    # Reorder columns to match the server's expected schema
    df = df[["timestamp", "arm", "reward"]]

    events = df.to_dict(orient="records")
    json.dump(events, output, indent=2)

    if output is not sys.stdout:
        click.echo(
            f"Successfully generated {num_events} events to {output.name}", err=True
        )


@generate_cli.command("weibull")
@click.option("--num-events", "-n", default=100, help="Number of events to generate.")
@click.option(
    "--alpha", default=1.5, help="Shape parameter of the Weibull distribution."
)
@click.option(
    "--beta", default=100.0, help="Scale parameter of the Weibull distribution."
)
@click.option(
    "--censoring-time", default=120.0, help="Time at which observations are censored."
)
@click.option(
    "--output",
    "-o",
    type=click.File("w"),
    default=sys.stdout,
    help="Output file path (defaults to stdout).",
)
def generate_weibull_cli_data(
    num_events: int,
    alpha: float,
    beta: float,
    censoring_time: float,
    output,
):
    """Generate dummy data for a Weibull survival analysis."""
    df = generate_weibull_data(
        alpha=alpha,
        beta=beta,
        num_events=num_events,
        censoring_time=censoring_time,
    )
    events = df.to_dict(orient="records")
    json.dump(events, output, indent=2)
    if output is not sys.stdout:
        click.echo(
            f"Successfully generated {num_events} events to {output.name}", err=True
        )


@generate_cli.command("hazard-rate")
@click.option("--num-events", "-n", default=200, help="Number of events to generate.")
@click.option(
    "--output",
    "-o",
    type=click.File("w"),
    default="-",
    help="Output file path (defaults to stdout).",
)
def generate_hazard_rate_cli_data(num_events: int, output):
    """Generate dummy survival data with a hump-shaped hazard rate."""
    df = generate_hump_shaped_hazard_data(num_events=num_events)
    events = df.to_dict(orient="records")
    json.dump(events, output, indent=2)
    if output is not sys.stdout:
        click.echo(
            f"Successfully generated {num_events} events to {output.name}", err=True
        )


@generate_cli.command("poisson-cohorts")
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
    help="Rate in 'cohort:event_type:rate' format, where rate is in events/day. "
    "Can be specified multiple times.",
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

    if start_date:
        ts_start = start_date
    else:
        ts_start = datetime.now() - timedelta(days=days)
    ts_end = ts_start + timedelta(days=days)

    all_events = []

    for cohort, event_type, rate in parsed_rates:
        # The rate is in events/day, which matches the default unit for the generator
        timestamps = generate_poisson_events(
            ts_start=ts_start,
            ts_end=ts_end,
            rate=rate,
            unit="day",
            random_seed=int(time.time()),
        )
        for ts in timestamps:
            all_events.append(
                {
                    "timestamp": datetime.fromtimestamp(ts).isoformat(),
                    "cohort": cohort,
                    "event_type": event_type,
                }
            )

    # Shuffle the events to mix the different streams together
    random.shuffle(all_events)
    total_events = len(all_events)

    json.dump(all_events, output, indent=2)
    if output is not sys.stdout:
        click.echo(
            f"Successfully generated {total_events} events to {output.name}", err=True
        )

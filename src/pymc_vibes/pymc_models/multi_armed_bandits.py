"""PyMC models for multi-armed bandits."""

import numpy as np
import pandas as pd


def fit_multi_armed_bandit(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """
    Fit a Bayesian multi-armed bandit model using a Beta-Bernoulli conjugate prior.

    This function processes raw event data (one row per arm pull with a binary
    'outcome' column) and calculates the posterior alpha and beta parameters for
    each arm's success probability distribution.

    Parameters
    ----------
    data : pd.DataFrame
        A DataFrame with columns 'arm' and 'outcome', where 'outcome' is binary (0 or 1).

    Returns
    -------
    pd.DataFrame
        A DataFrame indexed by 'arm' with columns 'alpha' and 'beta' representing
        the posterior parameters for each arm.
    """
    if not all(col in data.columns for col in ["arm", "outcome"]):
        raise ValueError("Input data must contain 'arm' and 'outcome' columns.")

    # Assume a Beta(1, 1) prior (uniform)
    prior_alpha = 1
    prior_beta = 1

    summary = (
        data.groupby("arm")["outcome"]
        .agg(["sum", "count"])
        .rename(columns={"sum": "successes"})
    )
    summary["failures"] = summary["count"] - summary["successes"]

    summary["alpha"] = prior_alpha + summary["successes"]
    summary["beta"] = prior_beta + summary["failures"]

    return summary[["alpha", "beta"]]


def thompson_sampling(
    posteriors: pd.DataFrame,
    magnitudes: pd.Series,
    n_samples: int = 10000,
    random_seed: int = None,
) -> pd.DataFrame:
    """
    Perform Thompson sampling on the expected reward (prob * magnitude).

    Parameters
    ----------
    posteriors : pd.DataFrame
        A DataFrame with 'arm' as the index and columns 'alpha' and 'beta'.
    magnitudes : pd.Series
        A Series with 'arm' as the index and the payout magnitude for each arm.
    n_samples : int, optional
        The number of random samples to draw.
    random_seed : int, optional
        A seed for the random number generator.

    Returns
    -------
    pd.DataFrame
        A DataFrame with 'arm' as the index and a 'prob_best' column.
    """
    rng = np.random.default_rng(random_seed)
    n_arms = len(posteriors)
    samples = np.zeros((n_samples, n_arms))

    for i, (arm, params) in enumerate(posteriors.iterrows()):
        prob_samples = rng.beta(params["alpha"], params["beta"], size=n_samples)
        expected_reward_samples = prob_samples * magnitudes.get(arm, 0)
        samples[:, i] = expected_reward_samples

    best_arm_indices = np.argmax(samples, axis=1)

    arm_names = posteriors.index
    prob_best = (
        pd.Series(best_arm_indices)
        .value_counts(normalize=True)
        .reindex(range(n_arms), fill_value=0)
    )
    prob_best.index = arm_names[prob_best.index]

    return pd.DataFrame({"prob_best": prob_best})


def _get_posterior_samples(
    posteriors: pd.DataFrame,
    magnitudes: pd.Series,
    n_samples: int = 1000,
    random_seed: int = None,
) -> dict[str, list[float]]:
    """
    Generate samples from the posterior distributions of success probability and expected reward.
    """
    rng = np.random.default_rng(random_seed)
    samples = {}

    for arm, params in posteriors.iterrows():
        prob_samples = rng.beta(params["alpha"], params["beta"], size=n_samples)
        reward_samples = prob_samples * magnitudes.get(arm, 0)
        samples[arm] = {
            "est_prob": prob_samples.tolist(),
            "expected_reward": reward_samples.tolist(),
        }

    return samples


def generate_mab_events(
    arm_params: dict[str, dict[str, float]],
    num_events: int,
    random_seed: int = None,
) -> pd.DataFrame:
    """
    Generate synthetic data for a MAB with success probability and magnitude.

    Parameters
    ----------
    arm_params : dict[str, dict[str, float]]
        A dictionary where keys are arm names and values are dicts containing
        'prob' (success probability) and 'magnitude' (payout on success).
    num_events : int
        The total number of events (arm pulls) to generate.
    random_seed : int, optional
        A seed for the random number generator.

    Returns
    -------
    pd.DataFrame
        A DataFrame with 'arm' and 'reward' columns.
    """
    rng = np.random.default_rng(random_seed)
    arms = list(arm_params.keys())

    chosen_arms = rng.choice(arms, size=num_events, replace=True)

    rewards = []
    for arm in chosen_arms:
        params = arm_params[arm]
        success = rng.random() < params["prob"]
        reward = params["magnitude"] if success else 0
        rewards.append(reward)

    return pd.DataFrame({"arm": chosen_arms, "reward": rewards})

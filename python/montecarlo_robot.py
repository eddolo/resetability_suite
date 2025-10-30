"""
Monte Carlo Robot Resetability Simulator
----------------------------------------
Generates randomized robot orientation sequences and evaluates
the SO(3) resetability metrics across noise levels and random seeds.
"""

import numpy as np
import pandas as pd
from tqdm import tqdm

from .so3_reset import (axang_to_quat, estimate_lambda_and_R,
                        predict_reset_benefit, quat_normalize)


def random_rotation_seq(n_steps=100, step_mean=0.02, step_std=0.01):
    """Generate a random sequence of small axis-angle increments."""
    seq = []
    for _ in range(n_steps):
        axis = np.random.randn(3)
        axis /= np.linalg.norm(axis) + 1e-12
        theta = abs(np.random.normal(step_mean, step_std))
        seq.append((axis, theta))
    return seq


def run_montecarlo(
    n_runs: int = 500,
    n_steps: int = 100,
    noise_sigma: float = 0.01,
    seed: int = 0,
) -> pd.DataFrame:
    """
    Run Monte Carlo resetability analysis.

    Parameters
    ----------
    n_runs : int
        Number of random trajectories to simulate.
    n_steps : int
        Number of axis-angle increments per trajectory.
    noise_sigma : float
        Standard deviation of random angular noise.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    DataFrame
        Columns: ['R', 'theta_net_deg', 'predicted_benefit_deg']
    """
    np.random.seed(seed)
    results = []

    for _ in tqdm(range(n_runs), desc="Monte Carlo robot runs"):
        seq = random_rotation_seq(n_steps, step_mean=0.02, step_std=noise_sigma)
        q_current = axang_to_quat([0, 0, 1], 0.05)  # nominal orientation
        try:
            lam, R, th_net = estimate_lambda_and_R(seq)
            benefit_deg, *_ = predict_reset_benefit(seq, q_current)
            results.append((R, np.degrees(th_net), benefit_deg))
        except Exception:
            results.append((np.nan, np.nan, np.nan))

    df = pd.DataFrame(results, columns=["R", "theta_net_deg", "predicted_benefit_deg"])
    return df


def summarize_results(df: pd.DataFrame):
    """Compute summary statistics of Monte Carlo output."""
    return {
        "mean_R": np.nanmean(df["R"]),
        "std_R": np.nanstd(df["R"]),
        "mean_theta_deg": np.nanmean(df["theta_net_deg"]),
        "mean_benefit_deg": np.nanmean(df["predicted_benefit_deg"]),
        "reset_opportunities": int((df["R"] < 0.05).sum()),
    }

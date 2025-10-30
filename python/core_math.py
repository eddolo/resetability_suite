# ==========================================================
# core_math.py
# ----------------------------------------------------------
# Core mathematical functions for SO(3) Resetability analysis.
# This is the single source of truth for math, used by all other modules.
# ==========================================================

import numpy as np
import pandas as pd
from so3_reset import (estimate_lambda_and_R, predict_reset_benefit, quat_conj,
                       quat_mul, quat_normalize, quat_to_axang)


def quat_error(q_ref, q):
    """Quaternion difference: q_err = q_ref * conj(q)"""
    return quat_mul(q_ref, quat_conj(q))


def quat_to_R(qw, qx, qy, qz):
    """Quaternion → rotation matrix (3×3)."""
    w, x, y, z = float(qw), float(qx), float(qy), float(qz)
    n = max(np.sqrt(w * w + x * x + y * y + z * z), 1e-15)
    w, x, y, z = w / n, x / n, y / n, z / n
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )


def analyze_from_quats(df, window=50, fps=10):
    """
    Compute Resetability metrics from quaternion telemetry:
      - R (resetability)
      - θ_net_deg (net rotation)
      - predicted_benefit_deg (predicted angular correction)
    """
    if df.empty or not all(c in df.columns for c in ["qw", "qx", "qy", "qz"]):
        return pd.DataFrame(), pd.DataFrame()

    quats = df[["qw", "qx", "qy", "qz"]].to_numpy()
    timestamps = (
        df["timestamp"].to_numpy()
        if "timestamp" in df.columns
        else np.arange(len(quats)) / max(fps, 1)
    )

    Rs, thetas, ts, benefits = [], [], [], []
    end = len(quats) - 1
    if end <= window:
        return pd.DataFrame(), pd.DataFrame()

    for i in range(window, end):
        seq = []
        for j in range(i - window, i):
            q1, q2 = quats[j], quats[j + 1]
            # Corrected: dq should be relative rotation from q1 to q2
            dq = quat_error(q2, q1)
            n, th = quat_to_axang(dq)
            seq.append((n, th))

        lam, R, th_net = estimate_lambda_and_R(seq)
        Rs.append(R)
        thetas.append(np.degrees(th_net))
        ts.append(timestamps[i])

        try:
            q_current = quat_normalize(quats[i])
            benefit_deg, *_ = predict_reset_benefit(seq, q_current)
        except Exception:
            benefit_deg = np.nan

        benefits.append(benefit_deg)

    results_df = pd.DataFrame(
        {
            "timestamp": ts,
            "R": Rs,
            "theta_net_deg": thetas,
            "predicted_benefit_deg": benefits,
        }
    )

    candidates_df = results_df[
        (results_df["R"] < 0.05)
        & (results_df["theta_net_deg"] > 1.0)
        & (results_df["predicted_benefit_deg"] > 0)
    ].copy()

    return results_df, candidates_df

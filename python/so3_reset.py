# python/so3_reset.py
# Minimal, dependency-light SO(3) resetability utilities (NumPy only).
# API:
#   - estimate_lambda_and_R(seq) -> (lambda, R, theta_net)
#   - compose_seq(seq) -> quaternion
#   - SO3ResetStream: push small increments then finalize/reset

from typing import List, Tuple

import numpy as np

Array = np.ndarray


def quat_mul(a: Array, b: Array) -> Array:
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array(
        [
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        ]
    )


def quat_normalize(q: Array) -> Array:
    return q / (np.linalg.norm(q) + 1e-15)


def axang_to_quat(n: Array, th: float) -> Array:
    n = np.asarray(n, float)
    n /= np.linalg.norm(n) + 1e-12
    c, s = np.cos(th / 2), np.sin(th / 2)
    return np.array([c, *(s * n)])


def quat_to_axang(q: Array) -> Tuple[Array, float]:
    q = quat_normalize(q)
    w = np.clip(q[0], -1.0, 1.0)
    th = 2 * np.arccos(w)
    if th < 1e-12:
        return np.array([1.0, 0.0, 0.0]), 0.0
    s = np.sqrt(max(1 - w * w, 1e-12))
    n = q[1:] / s
    return n, th


def compose_seq(seq: List[Tuple[Array, float]]) -> Array:
    q = np.array([1.0, 0.0, 0.0, 0.0])
    for n, th in seq:
        q = quat_mul(axang_to_quat(n, th), q)
    return quat_normalize(q)


def estimate_lambda_and_R(seq: List[Tuple[Array, float]]):
    """Return lambda=pi/theta_net, R=1-|w(q_reset)|, theta_net (rad).
    Here R≈0 means 'good reset' (low commutator residual)."""
    if not seq:
        return 1.0, 1.0, 0.0
    qnet = compose_seq(seq)
    _, th = quat_to_axang(qnet)
    lam = np.pi / th if th > 1e-12 else 1.0
    scaled = [(n, lam * thk) for (n, thk) in seq]
    q1 = compose_seq(scaled)
    qreset = quat_mul(q1, q1)  # apply scaled sequence twice
    R = 1.0 - abs(np.clip(qreset[0], -1.0, 1.0))  # corrected, treats q and -q same
    return float(lam), float(R), float(th)


class SO3ResetStream:
    """Streaming interface for controllers (push small body-frame increments)."""

    def __init__(self, window_sec: float = 0.2, dt: float = 0.005):
        self.dt = dt
        self.N = max(1, int(window_sec / dt))
        self.buf: List[Tuple[Array, float]] = []

    def push_axis_angle_increment(self, n: Array, dtheta: float):
        n = np.asarray(n, float)
        if np.linalg.norm(n) < 1e-12 or abs(dtheta) < 1e-12:
            return
        n = n / (np.linalg.norm(n) + 1e-12)
        self.buf.append((n, float(dtheta)))
        if len(self.buf) > self.N:
            self.buf.pop(0)

    def lambda_R_theta(self):
        return estimate_lambda_and_R(self.buf)

    def build_scaled_twice(self, lam: float):
        return [(n, lam * th) for (n, th) in self.buf] * 2


# -------------------------------------------------------
# Quaternion helper (now top-level, not inside class)
# -------------------------------------------------------
def quat_conj(q):
    """
    Quaternion conjugate: flips the vector part sign.
    Input q = [w, x, y, z]
    Returns q* = [w, -x, -y, -z]
    """
    q = np.asarray(q, dtype=float)
    return np.array([q[0], -q[1], -q[2], -q[3]])


# --------------------------------------------------------------------
# BEGIN NEW SECTION: Counterfactual Resetability Prediction
# --------------------------------------------------------------------
def predict_reset_benefit(
    seq: List[Tuple[Array, float]], q_current: Array
) -> Tuple[float, float, float, float, float, float]:
    """
    Estimate how much a λ-scaled reset would improve attitude recovery.

    Parameters
    ----------
    seq : list of (axis, angle)
        Recent rotation increments (same input as estimate_lambda_and_R)
    q_current : array([w,x,y,z])
        Current quaternion orientation (normalized)

    Returns
    -------
    benefit_deg : float
        Predicted benefit (reduction in residual error, degrees)
    residual_noreset_deg : float
        Predicted residual if system continues without reset
    residual_withreset_deg : float
        Predicted residual after λ-scaled double application
    lam : float
        Estimated λ (pi/theta_net)
    R : float
        Reset residual metric (lower is better)
    theta_net : float
        Net rotation angle (rad)
    """
    if not seq:
        return 0.0, 0.0, 0.0, 1.0, 1.0, 0.0

    lam, R, theta_net = estimate_lambda_and_R(seq)

    # Predict future attitude if continuing the current motion
    q_future = quat_mul(compose_seq(seq), q_current)
    _, th_noreset = quat_to_axang(q_future)

    # Predict attitude if we had applied a λ-scaled reset twice
    scaled_twice = [(n, lam * th) for (n, th) in seq] * 2
    q_reset = quat_mul(compose_seq(scaled_twice), q_current)
    _, th_withreset = quat_to_axang(q_reset)

    benefit_deg = np.degrees(th_noreset - th_withreset)
    return (
        float(benefit_deg),
        np.degrees(th_noreset),
        np.degrees(th_withreset),
        lam,
        R,
        theta_net,
    )


# --------------------------------------------------------------------
# END NEW SECTION
# --------------------------------------------------------------------

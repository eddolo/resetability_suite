import pandas as pd


def domain_info():
    return {
        "name": "Booster",
        "description": "Rocket booster telemetry — flight attitude and rotation rates.",
        "default_file": "data/telemetry.csv",
        "gravity": False,
    }


def load_telemetry(path: str) -> pd.DataFrame:
    """Load booster domain telemetry."""
    try:
        df = pd.read_csv(path)
    except Exception as e:
        raise RuntimeError(f"Failed to load booster telemetry: {e}")

    required = {"qw", "qx", "qy", "qz"}
    if not required.issubset(df.columns):
        raise ValueError(f"Booster CSV missing required columns: {required}")

    return df


def summarize_domain(results_df: pd.DataFrame) -> dict:
    """Booster-specific summary: reentry attitude stability."""
    if results_df.empty:
        return {"note": "No booster data"}

    R_mean = float(results_df["R"].mean())
    theta_mean = float(results_df["theta_net_deg"].mean())
    benefit_mean = float(results_df["predicted_benefit_deg"].mean())

    return {
        "Domain": "Booster",
        "Mean R": round(R_mean, 4),
        "Mean θ_net [deg]": round(theta_mean, 2),
        "Mean benefit [deg]": round(benefit_mean, 2),
        "Landing Readiness": (
            "🟢 Nominal" if R_mean < 0.25 else "🔴 Attitude correction required"
        ),
    }

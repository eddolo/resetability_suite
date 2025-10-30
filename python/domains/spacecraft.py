import pandas as pd


def domain_info():
    return {
        "name": "Spacecraft",
        "description": "Orbital or attitude control telemetry for spacecraft systems.",
        "default_file": "data/telemetry.csv",
        "gravity": False,
    }


def load_telemetry(path: str) -> pd.DataFrame:
    """Load spacecraft telemetry."""
    try:
        df = pd.read_csv(path)
    except Exception as e:
        raise RuntimeError(f"Failed to load spacecraft telemetry: {e}")

    required = {"qw", "qx", "qy", "qz"}
    if not required.issubset(df.columns):
        raise ValueError(f"Spacecraft CSV missing required columns: {required}")

    return df


def summarize_domain(results_df: pd.DataFrame) -> dict:
    """Spacecraft-specific summary: orientation and stability metrics."""
    if results_df.empty:
        return {"note": "No data available"}

    R_mean = float(results_df["R"].mean())
    theta_mean = float(results_df["theta_net_deg"].mean())
    benefit_mean = float(results_df["predicted_benefit_deg"].mean())

    stability = (
        "🛰️ Stable attitude" if R_mean < 0.2 else "⚠️ Possible control instability"
    )

    return {
        "Domain": "Spacecraft",
        "Mean R": round(R_mean, 4),
        "Mean θ_net [deg]": round(theta_mean, 2),
        "Mean benefit [deg]": round(benefit_mean, 2),
        "Status": stability,
        "Comment": "Lower R means better attitude convergence.",
    }

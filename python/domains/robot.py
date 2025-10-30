import pandas as pd


def domain_info():
    return {
        "name": "Robot",
        "description": "Local robot pose or IMU-based attitude telemetry.",
        "default_file": "data/telemetry.csv",
        "gravity": True,
    }


def load_telemetry(path: str) -> pd.DataFrame:
    """Load robot domain telemetry (CSV with quaternion columns)."""
    try:
        df = pd.read_csv(path)
    except Exception as e:
        raise RuntimeError(f"Failed to load robot telemetry: {e}")

    required = {"qw", "qx", "qy", "qz"}
    if not required.issubset(df.columns):
        raise ValueError(f"Robot CSV missing required columns: {required}")

    return df


def summarize_domain(results_df: pd.DataFrame) -> dict:
    """Robot-specific summary: orientation consistency and reset health."""
    if results_df.empty:
        return {"note": "No data to summarize"}

    R_mean = float(results_df["R"].mean())
    theta_mean = float(results_df["theta_net_deg"].mean())
    benefit_mean = float(results_df["predicted_benefit_deg"].mean())

    return {
        "Domain": "Robot",
        "Mean R": round(R_mean, 4),
        "Mean θ_net [deg]": round(theta_mean, 2),
        "Mean benefit [deg]": round(benefit_mean, 2),
        "Health": "✅ Stable orientation" if R_mean < 0.3 else "⚠️ Excess drift",
    }

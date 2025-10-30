# ==========================================================
# ui_helpers.py
# ----------------------------------------------------------
# Reusable Streamlit utilities for data loading, plotting,
# and visualization used across all tabs.
# ==========================================================

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from python.core_math import quat_to_R


# ==========================================================
# UI Components
# ==========================================================
def render_status_bar(
    st, domain, domain_colors, sim_mode, running, sim_idx, total_frames
):
    """Renders the top status bar with a pulsing dot for live status."""
    color = domain_colors.get(domain, "#ccc")
    mode_txt = "Simulation" if sim_mode else "Live"

    pulse_css = """
    <style>
    @keyframes pulse {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.4); opacity: 0.4; }
        100% { transform: scale(1); opacity: 1; }
    }
    .live-dot {
        display:inline-block;
        width:12px; height:12px;
        border-radius:50%;
        margin-right:6px;
        background-color:#00cc66;
        animation:pulse 1s infinite ease-in-out;
    }
    .paused-dot {
        display:inline-block;
        width:12px; height:12px;
        border-radius:50%;
        margin-right:6px;
        background-color:#cc3333;
    }
    </style>
    """
    st.markdown(pulse_css, unsafe_allow_html=True)

    dot_class = "live-dot" if running else "paused-dot"
    html = f"""
    <div style="background-color:{color}20;padding:8px 14px;border-radius:10px;margin-bottom:12px;">
        <span class="{dot_class}"></span>
        <b style="color:{color};font-size:1.1em;">{domain}</b> &nbsp; | &nbsp;
        <span style="font-weight:600;">Mode:</span> {mode_txt} &nbsp; | &nbsp;
        <span style="font-weight:600;">Frames:</span> {sim_idx}/{total_frames}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ==========================================================
# Data loading & Aggregation
# ==========================================================
@st.cache_data(show_spinner=False, ttl=1.0)
def load_domain_telemetry(domain_module, path):
    """Load telemetry CSV via domain-specific loader, safely cached."""
    try:
        return domain_module.load_telemetry(path)
    except Exception as e:
        st.error(f"Failed to load telemetry for {domain_module.__name__}: {e}")
        return pd.DataFrame()


@st.cache_data(show_spinner=False)
def make_summary_table(df):
    """Aggregate results by domain for quick summary."""
    if df.empty:
        return pd.DataFrame()
    return (
        df.groupby("domain")
        .agg(
            count=("R", "count"),
            mean_R=("R", "mean"),
            mean_theta=("theta_net_deg", "mean"),
            mean_benefit=("predicted_benefit_deg", "mean"),
        )
        .reset_index()
    )


# ==========================================================
# 3D attitude visualization
# ==========================================================
def make_cube_traces(R, scale=0.25):
    """Generate cube + body axes Plotly traces given rotation matrix R."""
    s = scale
    corners = np.array(
        [
            [-s, -s, -s],
            [s, -s, -s],
            [s, s, -s],
            [-s, s, -s],
            [-s, -s, s],
            [s, -s, s],
            [s, s, s],
            [-s, s, s],
        ]
    )
    Cw = corners @ R.T
    edges = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 0),
        (4, 5),
        (5, 6),
        (6, 7),
        (7, 4),
        (0, 4),
        (1, 5),
        (2, 6),
        (3, 7),
    ]
    xe, ye, ze = [], [], []
    for a, b in edges:
        xa, ya, za = Cw[a]
        xb, yb, zb = Cw[b]
        xe += [xa, xb, None]
        ye += [ya, yb, None]
        ze += [za, zb, None]
    cube = go.Scatter3d(x=xe, y=ye, z=ze, mode="lines", line=dict(width=4), name="Body")
    axes_len = 0.5
    ax_traces = [
        go.Scatter3d(
            x=[0, (R.T @ [axes_len, 0, 0])[0]],
            y=[0, (R.T @ [axes_len, 0, 0])[1]],
            z=[0, (R.T @ [axes_len, 0, 0])[2]],
            mode="lines",
            line=dict(width=6, color="red"),
            name="X",
        ),
        go.Scatter3d(
            x=[0, (R.T @ [0, axes_len, 0])[0]],
            y=[0, (R.T @ [0, axes_len, 0])[1]],
            z=[0, (R.T @ [0, axes_len, 0])[2]],
            mode="lines",
            line=dict(width=6, color="green"),
            name="Y",
        ),
        go.Scatter3d(
            x=[0, (R.T @ [0, 0, axes_len])[0]],
            y=[0, (R.T @ [0, 0, axes_len])[1]],
            z=[0, (R.T @ [0, 0, axes_len])[2]],
            mode="lines",
            line=dict(width=6, color="blue"),
            name="Z",
        ),
    ]
    return [cube] + ax_traces


def make_3d_figure(qw, qx, qy, qz):
    """Render 3D cube for given quaternion."""
    R = quat_to_R(qw, qx, qy, qz)
    traces = make_cube_traces(R)
    fig = go.Figure(data=traces)
    fig.update_layout(
        scene=dict(
            xaxis=dict(range=[-0.8, 0.8]),
            yaxis=dict(range=[-0.8, 0.8]),
            zaxis=dict(range=[-0.8, 0.8]),
            aspectmode="cube",
        ),
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
        height=420,
    )
    return fig


@st.cache_data(show_spinner=False)
def cached_3d_figure(qw, qx, qy, qz):
    """Cached version of 3D orientation cube."""
    return make_3d_figure(qw, qx, qy, qz)


# ==========================================================
# 2D metric plots
# ==========================================================
def plot_metrics(
    results_df,
    candidates_df,
    highlight_ts=None,
    smooth_mode="None",
    smooth_strength=10,
    smooth_window=20,
):
    """Plot R, θ_net, predicted benefit with smoothing & highlight."""
    if results_df.empty:
        st.info("No data available to plot yet.")
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.text(0.5, 0.5, "Waiting for data...", ha="center", va="center")
        st.pyplot(fig, clear_figure=True)
        return

    df_plot = results_df.copy()
    df_plot["R_smooth"] = (
        df_plot["R"].rolling(window=smooth_window, min_periods=1).mean()
    )
    fig, ax1 = plt.subplots(figsize=(10, 4))

    if smooth_mode != "None":
        if smooth_mode == "Rolling Mean":
            df_plot["R"] = df_plot["R"].rolling(smooth_strength, min_periods=1).mean()
            df_plot["theta_net_deg"] = (
                df_plot["theta_net_deg"].rolling(smooth_strength, min_periods=1).mean()
            )
            df_plot["predicted_benefit_deg"] = (
                df_plot["predicted_benefit_deg"]
                .rolling(smooth_strength, min_periods=1)
                .mean()
            )
        elif smooth_mode == "Exponential Filter (EWMA)":
            alpha = 2 / (smooth_strength + 1)
            df_plot["R"] = df_plot["R"].ewm(alpha=alpha).mean()
            df_plot["theta_net_deg"] = df_plot["theta_net_deg"].ewm(alpha=alpha).mean()
            df_plot["predicted_benefit_deg"] = (
                df_plot["predicted_benefit_deg"].ewm(alpha=alpha).mean()
            )

    ax1.plot(
        df_plot["timestamp"], df_plot["R"], color="blue", alpha=0.4, label="R (raw)"
    )
    ax1.plot(
        df_plot["timestamp"],
        df_plot["R_smooth"],
        color="blue",
        linewidth=2.2,
        label=f"R (mean {smooth_window})",
    )
    ax1.set_xlabel("Time [s]")
    ax1.set_ylabel("R", color="blue")
    ax2 = ax1.twinx()
    ax2.plot(
        df_plot["timestamp"],
        df_plot["theta_net_deg"],
        color="orange",
        label="θ_net [deg]",
    )
    ax2.set_ylabel("θ_net [deg]", color="orange")
    ax3 = ax1.twinx()
    ax3.spines["right"].set_position(("outward", 60))
    ax3.plot(
        df_plot["timestamp"],
        df_plot["predicted_benefit_deg"],
        color="green",
        linestyle="--",
        label="Predicted Δθ [deg]",
    )
    ax3.set_ylabel("Predicted Δθ [deg]", color="green")
    if not candidates_df.empty:
        ax1.scatter(
            candidates_df["timestamp"],
            candidates_df["R"],
            color="red",
            s=20,
            label="Reset Opportunity",
        )
    if highlight_ts is not None:
        try:
            nearest_idx = (df_plot["timestamp"] - highlight_ts).abs().idxmin()
            ts_val = df_plot.loc[nearest_idx, "timestamp"]
            R_val = df_plot.loc[nearest_idx, "R"]
            ax1.scatter(
                ts_val,
                R_val,
                color="lime",
                s=80,
                edgecolor="black",
                zorder=5,
                label="Replayed Event",
            )
            ax1.axvline(ts_val, color="lime", linestyle="--", alpha=0.6)
        except (KeyError, ValueError):
            pass
    lines, labels = [], []
    for ax in [ax1, ax2, ax3]:
        l, lab = ax.get_legend_handles_labels()
        lines += l
        labels += lab
    if lines:
        ax1.legend(lines, labels, loc="upper right", fontsize=8)
    plt.tight_layout()
    st.pyplot(fig, clear_figure=True)

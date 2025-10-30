# ==========================================================
# ui_live.py
# ----------------------------------------------------------
# Live / Simulation tab for the SO(3) Resetability Control Suite
# This module handles UI layout, state management, and calls
# shared helpers for plotting and analysis.
# ==========================================================

import time
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import subprocess
import sys

# --- Import from shared modules ---
from python.core_math import analyze_from_quats
from python.events import EventLogger
from python.ui_helpers import (
    cached_3d_figure,
    load_domain_telemetry,
    plot_metrics,
    render_status_bar,
)
from live_data_logger import get_serial_ports

# --- Import for new feature ---
from python.report_utils import make_summary, export_pdf

def on_domain_change():
    """Called when the user selects a new domain."""
    # The new value is already in session_state thanks to the key='selected_domain'
    # We just need to update the URL query parameter to match.
    st.query_params["domain"] = st.session_state.selected_domain
    # Reset simulation on switch to avoid confusion
    st.session_state.sim_idx = 0
    st.session_state.running = False

# ==========================================================
# Main renderer
# ==========================================================
def render_live_tab(st, DOMAIN_MAP, DOMAIN_COLORS):
    ss = st.session_state

    # --- Initialize session state for logger and auto-report ---
    if 'logger_process' not in ss:
        ss.logger_process = None
    if 'serial_ports' not in ss:
        ss.serial_ports = []
    if 'last_report_path' in ss and ss.last_report_path:
        del ss.last_report_path # Clean up old report paths on reload

    # --- Handle external replay triggers ---
    if "selected_event" in ss and ss.selected_event:
        evt = ss.selected_event
        st.info(
            f"🎞 Replaying logged event from {evt['domain']} at t={evt['timestamp']:.2f}s "
            f"(R={evt['R']:.4f}, Δθ={evt['predicted_benefit_deg']:.2f}°)"
        )
        ss.sim_mode = True
        ss.running = False
        ss.selected_domain = evt["domain"]
        ss.last_event_ts = evt["timestamp"]
        del ss.selected_event

    # (This code goes inside the render_live_tab function in python/ui_live.py)

    # --- Sidebar Controls ---
    with st.sidebar:
        st.markdown("### Domain")
        domain_names = list(DOMAIN_MAP.keys())

        # The 'key' parameter is enough. Streamlit will automatically find the correct
        # index by looking at the value of st.session_state.selected_domain.
        # This removes the warning.
        st.selectbox(
            "Choose application domain:",
            domain_names,
            key="selected_domain",
            on_change=on_domain_change
        )

        # The rest of the code now reliably uses the value from session_state
        domain_module = DOMAIN_MAP[ss.selected_domain]
        info = getattr(domain_module, "domain_info", lambda: {})()
        st.caption(info.get("description", ""))
        default_file = info.get("default_file", "data/telemetry.csv")
        if info.get("gravity", False):
            st.info("🌍 Gravity calibration enabled for this domain.")

        st.markdown("### Mode")
        # Added keys to all widgets to make them more robust
        st.toggle("🧪 Simulation mode (replay CSV)", key='sim_mode')
        st.text_input("Telemetry CSV path", value=default_file, key='csv_path')
        st.slider("Window (samples)", 10, 300, 50, 5, key='window')
        st.slider("Refresh rate [Hz]", 1, 20, 10, key='refresh_hz')
        st.number_input("Assumed FPS (if no timestamps)", 1, 1000, 10, key='fps_assumed')

        if ss.sim_mode:
            st.markdown("---")
            st.markdown("### Simulation Playback")
            st.select_slider("Playback speed", [0.5, 1.0, 2.0, 5.0], 1.0, key='speed')
            st.toggle("⏸ Pause on reset opportunity", True, key='pause_on_reset')
            adaptive_window = st.toggle("🧠 Adaptive window (seconds)", False, key='adaptive_window')
            st.slider("Window (sec)", 0.05, 5.0, 0.5, 0.05, disabled=not adaptive_window, key='window_seconds')

        # --- Live Data Logger UI Section ---
        st.markdown("---")
        st.markdown("### 🛰️ Live Data Logger")
        if st.button("Scan for Serial Ports"):
            with st.spinner("Scanning..."):
                ss.serial_ports = get_serial_ports()
                if not ss.serial_ports: st.warning("No serial ports found.")
                else: st.success(f"Found ports: {', '.join(ss.serial_ports)}")

        if ss.serial_ports:
            selected_port = st.selectbox("Select Port", ss.serial_ports)
            c1, c2 = st.columns(2)
            if c1.button("▶️ Start Logging"):
                if ss.logger_process is None:
                    cmd = [sys.executable, "live_data_logger.py", "--port", selected_port]
                    ss.logger_process = subprocess.Popen(cmd)
                    st.success(f"Started logging from {selected_port}"); st.rerun()
                else: st.warning("Logger is already running.")
            if c2.button("⏹️ Stop Logging"):
                if ss.logger_process is not None:
                    ss.logger_process.terminate(); ss.logger_process = None
                    st.info("Logger stopped."); st.rerun()
                else: st.warning("Logger is not running.")
        else: st.caption("Click 'Scan' to find connected devices.")
        if ss.logger_process is not None: st.success(f"🟢 Logging active (PID: {ss.logger_process.pid})")
        else: st.info("⚪ Logger inactive.")

        # --- Simulation Controls ---
        st.markdown("---")
        st.markdown("### 🔬 Simulation Controls")
        c1, c2, c3 = st.columns(3)
        start = c1.button("▶ Start")
        pause = c2.button("⏸ Pause")
        reset = c3.button("⏹ Stop")
        auto_report = st.toggle("📄 Auto-generate report on stop", value=True)

    # --- Load Data ---
    # Get the path from session_state, using the key we assigned in the sidebar
    path = ss.csv_path
    file = Path(path)
    if not file.exists():
        st.warning(f"Waiting for file: {file.resolve()}")
        st.stop()
    full_df = load_domain_telemetry(domain_module, path)
    if full_df.empty: st.warning("No data loaded yet — waiting for telemetry..."); st.stop()

    # --- Simulation or Live Mode Logic ---
    if "timestamp" in full_df.columns and len(full_df) > 1:
        src_hz = 1.0 / max(np.median(np.diff(full_df["timestamp"].values)), 1e-6)
    else: src_hz = float(fps_assumed)
    # Retrieve widget values from session_state using their keys
    adaptive_window = ss.adaptive_window
    window = ss.window
    window_seconds = ss.window_seconds
    speed = ss.speed
    refresh_hz = ss.refresh_hz
    fps_assumed = ss.fps_assumed
    pause_on_reset = ss.pause_on_reset
    
    eff_window = (
        int(max(10, round(window_seconds * src_hz))) if adaptive_window else int(window)
    )

    if ss.sim_mode:
        if ss.running:
            frames_per_tick = max(1, int(round(src_hz * speed / refresh_hz)))
            ss.sim_idx = (ss.sim_idx + frames_per_tick) % (len(full_df) + 1)
        view_df = full_df.iloc[:max(2, ss.sim_idx)].copy()
    else: view_df = full_df.copy()

    # --- Button actions & Auto-Report Logic ---
    if start: ss.running = True; st.rerun()
    if pause: ss.running = False; st.rerun()
    if reset:
        was_running = ss.running
        ss.running = False
        if was_running and auto_report and not view_df.empty:
            st.toast("⚙️ Generating final mission summary...")
            final_results, _ = analyze_from_quats(view_df, window=eff_window, fps=int(fps_assumed))
            if not final_results.empty:
                summary_data = make_summary(final_results)
                report_path = Path("results/mission_summary.pdf")
                report_path.parent.mkdir(parents=True, exist_ok=True)
                export_pdf(summary_data, str(report_path))
                ss.last_report_path = str(report_path)
                st.sidebar.success("Report saved!")
            else: st.sidebar.warning("Not enough data for report.")
        ss.sim_idx = 0; ss.last_event_ts = -1e18
        st.rerun()

    # --- Display Download Button for Auto-Report ---
    if 'last_report_path' in ss and ss.last_report_path:
        with open(ss.last_report_path, "rb") as f:
            st.sidebar.download_button("📥 Download Last Report", f, "mission_summary.pdf", "application/pdf")
        del ss.last_report_path

    # --- Handle replay jump ---
    if "last_event_ts" in ss and ss.last_event_ts > 0 and "timestamp" in full_df.columns:
        closest_idx = (full_df["timestamp"] - ss.last_event_ts).abs().idxmin()
        ss.sim_idx = max(2, int(closest_idx))

    # --- Render Status Bar & Main UI ---
    render_status_bar(st, ss.selected_domain, DOMAIN_COLORS, ss.sim_mode, ss.running, ss.sim_idx, len(full_df))
    st.markdown("### Plot Smoothing")
    smooth_mode = st.selectbox("Method", ["None", "Rolling Mean", "Exponential Filter (EWMA)"], index=0, key='smooth_mode')
    smooth_strength = st.slider("Strength", 1, 50, 10, key='smooth_strength')

    # --- Analysis ---
    results_df, candidates_df = analyze_from_quats(view_df, window=eff_window, fps=int(fps_assumed))

    # --- Auto-pause & Log ---
    if pause_on_reset and not candidates_df.empty and ss.running:
        latest_ts = float(candidates_df["timestamp"].max())
        if latest_ts > ss.get("last_event_ts", -1e18):
            last_row = candidates_df.loc[candidates_df["timestamp"] == latest_ts].iloc[-1]
            if "event_logger" not in ss: ss.event_logger = EventLogger()
            log_path = ss.event_logger.log(ts=latest_ts, domain=ss.selected_domain, R=float(last_row["R"]),
                                           theta_deg=float(last_row["theta_net_deg"]),
                                           benefit_deg=float(last_row["predicted_benefit_deg"]))
            ss.running = False; ss.last_event_ts = latest_ts
            st.success(f"⏸ Paused at reset opportunity (t={latest_ts:.3f}s). Event logged → {log_path}")

    # --- Layout & Display ---
    col_main, col_3d = st.columns([1.2, 1])
    with col_main:
        highlight_ts = ss.last_event_ts if ss.last_event_ts > 0 else None
        plot_metrics(results_df, candidates_df, highlight_ts, smooth_mode, smooth_strength, 20)
        if highlight_ts: ss.last_event_ts = -1e18
        if ss.sim_mode:
            pct = 100.0 * ss.sim_idx / max(1, len(full_df))
            st.progress(pct / 100.0, text=f"Timeline: {pct:.1f}% of run")

    with col_3d:
        if not view_df.empty:
            qw, qx, qy, qz = view_df[["qw", "qx", "qy", "qz"]].iloc[-1].tolist()
            st.plotly_chart(cached_3d_figure(qw, qx, qy, qz), width='stretch')
        else:  # Default cube
            st.plotly_chart(cached_3d_figure(1, 0, 0, 0), width='stretch')

    # --- Bottom metrics and data ---
    m_r, m_th, m_ben, m_w = st.columns(4)
    m_r.metric("Mean R", f"{results_df['R'].mean():.6f}" if not results_df.empty else "N/A")
    m_th.metric("Mean θ_net [deg]", f"{results_df['theta_net_deg'].mean():.3f}" if not results_df.empty else "N/A")
    m_ben.metric("Mean Δθ [deg]", f"{results_df['predicted_benefit_deg'].mean():.2f}" if not results_df.empty else "N/A")
    if all(c in view_df.columns for c in ["wx", "wy", "wz"]):
        mean_w = np.nanmean(np.linalg.norm(view_df[["wx", "wy", "wz"]].to_numpy(), axis=1))
        m_w.metric("Mean |ω| [rad/s]", f"{mean_w:.3f}")
    if not candidates_df.empty: st.dataframe(candidates_df.tail(10), use_container_width=True, height=240)
    else: st.info("No reset opportunities detected yet.")

    # --- Auto-refresh trigger ---
    if ss.running:
        time.sleep(max(0.02, 1.0 / refresh_hz))
        st.rerun()
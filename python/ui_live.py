# ==========================================================
# ui_live.py (Version 4 - Final and Complete)
# ==========================================================
# Live / Simulation tab for the SO(3) Resetability Control Suite.
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
from python.report_utils import make_summary, export_pdf

def on_domain_change():
    """Called when the user selects a new domain from the sidebar."""
    st.query_params["domain"] = st.session_state.selected_domain
    st.session_state.sim_idx = 0
    st.session_state.running = False

def find_csv_files(directory="data"):
    """Finds all .csv files in the specified directory."""
    path = Path(directory)
    if not path.is_dir():
        return []
    return [str(f) for f in path.glob("*.csv")]

# ==========================================================
# Main Renderer
# ==========================================================
def render_live_tab(st, DOMAIN_MAP, DOMAIN_COLORS):
    ss = st.session_state

    # --- Initialize session state keys ---
    ss.setdefault('logger_process', None)
    ss.setdefault('serial_ports', [])
    if 'last_report_path' in ss:
        del ss.last_report_path

    # --- Handle external replay triggers ---
    if "selected_event" in ss and ss.selected_event:
        evt = ss.selected_event
        st.info(f"🎞 Replaying logged event: {evt['domain']} @ t={evt['timestamp']:.2f}s")
        ss.sim_mode = True
        ss.running = False
        ss.selected_domain = evt["domain"]
        ss.last_event_ts = evt["timestamp"]
        del ss.selected_event

    # --- Sidebar Controls ---
    with st.sidebar:
        st.markdown("### Domain")
        st.selectbox(
            "Choose application domain:",
            list(DOMAIN_MAP.keys()),
            key="selected_domain",
            on_change=on_domain_change
        )
        domain_module = DOMAIN_MAP[ss.selected_domain]
        info = getattr(domain_module, "domain_info", lambda: {})()
        st.caption(info.get("description", ""))
        default_file = info.get("default_file", "data/telemetry.csv")
        if info.get("gravity", False): st.info("🌍 Gravity calibration enabled.")

        st.markdown("### Telemetry Source")

        # Find existing CSV files
        existing_files = find_csv_files()
        
        # Let the user choose the source
        source_option = st.radio(
            "Choose data source:",
            ["Select an existing file", "Upload a new file"],
            key='source_option'
        )

        uploaded_file = None
        if ss.source_option == "Select an existing file":
            if not existing_files:
                st.warning("No CSV files found in the 'data/' directory.")
                st.stop() # Stop execution if no files are available
            
            # Use a dropdown for existing files
            st.selectbox("Select a telemetry file:", existing_files, key='csv_path')

        elif ss.source_option == "Upload a new file":
            uploaded_file = st.file_uploader(
                "Upload your telemetry CSV",
                type=["csv"]
            )
            if uploaded_file is not None:
                # When a file is uploaded, we will use it directly.
                # The 'path' variable will be handled in the main logic section.
                ss.csv_path = uploaded_file
            else:
                st.info("Please upload a CSV file to begin.")
                st.stop()
        
        st.markdown("### Mode & Analysis")
        st.toggle("🧪 Simulation mode", key='sim_mode')
        st.slider("Window (samples)", 10, 300, 50, 5, key='window')
        st.slider("Refresh rate [Hz]", 1, 20, 10, key='refresh_hz')
        st.number_input("Assumed FPS", 1, 1000, 10, key='fps_assumed')

        if ss.get('sim_mode', True):
            st.markdown("---")
            st.markdown("### Simulation Playback")
            st.select_slider("Playback speed", [0.5, 1.0, 2.0, 5.0], 1.0, key='speed')
            st.toggle("⏸ Pause on reset opportunity", True, key='pause_on_reset')
            st.toggle("🧠 Adaptive window", False, key='adaptive_window')
            st.slider("Window (sec)", 0.05, 5.0, 0.5, 0.05, disabled=not ss.get('adaptive_window', False), key='window_seconds')
        else:
            ss.setdefault('speed', 1.0)
            ss.setdefault('pause_on_reset', False)
            ss.setdefault('adaptive_window', False)
            ss.setdefault('window_seconds', 0.5)

        st.markdown("---")
        st.markdown("### 🛰️ Live Data Logger")
        if st.button("Scan for Serial Ports"):
            with st.spinner("Scanning..."): ss.serial_ports = get_serial_ports()
        if ss.serial_ports:
            selected_port = st.selectbox("Select Port", ss.serial_ports)
            c1, c2 = st.columns(2)
            if c1.button("▶️ Start Logging"):
                if ss.logger_process is None:
                    cmd = [sys.executable, "live_data_logger.py", "--port", selected_port]
                    ss.logger_process = subprocess.Popen(cmd)
                    st.success(f"Logging from {selected_port}"); st.rerun()
            if c2.button("⏹️ Stop Logging"):
                if ss.logger_process is not None:
                    ss.logger_process.terminate(); ss.logger_process = None
                    st.info("Logger stopped."); st.rerun()
        if ss.logger_process: st.success(f"🟢 Logging active (PID: {ss.logger_process.pid})")
        else: st.info("⚪ Logger inactive.")

        st.markdown("---")
        st.markdown("### 🔬 Simulation Controls")
        c1, c2, c3 = st.columns(3)
        start = c1.button("▶ Start")
        pause = c2.button("⏸ Pause")
        reset = c3.button("⏹ Stop")
        st.toggle("📄 Auto-generate report on stop", value=True, key='auto_report')

    # --- Retrieve all values from session state for use in logic ---
    path = ss.csv_path
    window = ss.window
    refresh_hz = ss.refresh_hz
    fps_assumed = ss.fps_assumed
    sim_mode = ss.sim_mode
    speed = ss.get('speed', 1.0)
    pause_on_reset = ss.get('pause_on_reset', False)
    adaptive_window = ss.get('adaptive_window', False)
    window_seconds = ss.get('window_seconds', 0.5)
    auto_report = ss.get('auto_report', True)

    # --- Load Data ---
    # The 'path' variable now comes from session_state, set by the new file handler
    path_or_buffer = ss.csv_path
    
    # The load_domain_telemetry function can accept a path OR an uploaded file object
    full_df = load_domain_telemetry(domain_module, path_or_buffer)
    
    if full_df.empty:
        # Give a more specific message if waiting for an upload
        if ss.source_option == "Upload a new file" and uploaded_file is None:
             st.info("Waiting for file upload...")
        else:
             st.warning("No data loaded yet or file is empty.")
        st.stop()

    # --- Button actions & State Update Logic ---
    if start: ss.running = True; st.rerun()
    if pause: ss.running = False; st.rerun()
    if reset:
        was_running = ss.running
        ss.running = False
        if was_running and auto_report and not full_df.empty:
            st.toast("⚙️ Generating final mission summary...")
            sim_df_final = full_df.iloc[:max(2, ss.sim_idx)].copy()
            eff_window_final = int(max(10, round(window_seconds * (1/max(np.median(np.diff(sim_df_final["timestamp"].values)), 1e-6))))) if adaptive_window else int(window)
            final_results, _ = analyze_from_quats(sim_df_final, window=eff_window_final, fps=int(fps_assumed))
            if not final_results.empty:
                final_candidates = final_results[(final_results["R"] < 0.05) & (final_results["predicted_benefit_deg"] > 0)]
                summary_data = make_summary(final_results)
                report_path = Path("results/mission_summary.pdf")
                report_path.parent.mkdir(parents=True, exist_ok=True)
                export_pdf(summary_data, final_results, final_candidates, str(report_path))
                ss.last_report_path = str(report_path)
                st.sidebar.success("Report saved!")
            else: st.sidebar.warning("Not enough data for report.")
        ss.sim_idx = 0; ss.last_event_ts = -1e18
        st.rerun()
    
    # --- Simulation Progression ---
    view_df = full_df.copy() # Default to full data for Live Mode
    if sim_mode:
        if ss.running:
            src_hz = 1.0 / max(np.median(np.diff(full_df["timestamp"].values)), 1e-6) if "timestamp" in full_df.columns and len(full_df) > 1 else float(fps_assumed)
            frames_per_tick = max(1, int(round(speed * src_hz / refresh_hz)))
            ss.sim_idx += frames_per_tick
            if ss.sim_idx >= len(full_df):
                ss.sim_idx = len(full_df)
                ss.running = False
                st.toast("✅ Simulation finished!")
        view_df = full_df.iloc[:max(2, ss.sim_idx)].copy()

    # --- Display Download Button ---
    if 'last_report_path' in ss and ss.last_report_path:
        with open(ss.last_report_path, "rb") as f:
            st.sidebar.download_button("📥 Download Last Report", f, "mission_summary.pdf", "application/pdf")
        del ss.last_report_path

    # --- Handle Replay Jump ---
    if "last_event_ts" in ss and ss.last_event_ts > 0 and "timestamp" in full_df.columns:
        closest_idx = (full_df["timestamp"] - ss.last_event_ts).abs().idxmin()
        ss.sim_idx = max(2, int(closest_idx))

    # --- Render Main UI ---
    render_status_bar(st, ss.selected_domain, DOMAIN_COLORS, sim_mode, ss.running, ss.sim_idx, len(full_df))
    st.markdown("### Plot Smoothing")
    st.selectbox("Method", ["None", "Rolling Mean", "Exponential Filter (EWMA)"], key='smooth_mode')
    st.slider("Strength", 1, 50, 10, key='smooth_strength')

    # --- Analysis ---
    eff_window = int(max(10, round(window_seconds * (1.0 / max(np.median(np.diff(view_df["timestamp"].values)), 1e-6) if "timestamp" in view_df.columns and len(view_df) > 1 else float(fps_assumed))))) if adaptive_window else int(window)
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
        plot_metrics(results_df, candidates_df, highlight_ts, ss.smooth_mode, ss.smooth_strength, 20)
        if highlight_ts: ss.last_event_ts = -1e18
        if sim_mode:
            pct = 100.0 * ss.sim_idx / max(1, len(full_df))
            st.progress(pct / 100.0, text=f"Timeline: {pct:.1f}% of run")

    with col_3d:
        if not view_df.empty:
            qw, qx, qy, qz = view_df[["qw", "qx", "qy", "qz"]].iloc[-1].tolist()
            st.plotly_chart(cached_3d_figure(qw, qx, qy, qz), width='stretch')
        else: st.plotly_chart(cached_3d_figure(1, 0, 0, 0), width='stretch')

    # --- Bottom Metrics ---
    m_r, m_th, m_ben, m_w = st.columns(4)
    m_r.metric("Mean R", f"{results_df['R'].mean():.6f}" if not results_df.empty else "N/A")
    m_th.metric("Mean θ_net [deg]", f"{results_df['theta_net_deg'].mean():.3f}" if not results_df.empty else "N/A")
    m_ben.metric("Mean Δθ [deg]", f"{results_df['predicted_benefit_deg'].mean():.2f}" if not results_df.empty else "N/A")
    if all(c in view_df.columns for c in ["wx", "wy", "wz"]):
        mean_w = np.nanmean(np.linalg.norm(view_df[["wx", "wy", "wz"]].to_numpy(), axis=1))
        m_w.metric("Mean |ω| [rad/s]", f"{mean_w:.3f}")
    if not candidates_df.empty: st.dataframe(candidates_df.tail(10), width='stretch', height=240)
    else: st.info("No reset opportunities detected yet.")

    # --- Auto-refresh Trigger ---
    if ss.running:
        time.sleep(max(0.02, 1.0 / refresh_hz))
        st.rerun()
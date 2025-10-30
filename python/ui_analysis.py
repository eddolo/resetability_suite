# ==========================================================
# ui_analysis.py (Final, Replay Button Fixed)
# ==========================================================
from pathlib import Path
import streamlit as st
import pandas as pd

# --- Import from shared modules ---
from python.ui_helpers import make_summary_table
from python.report_utils import export_pdf

# ----------------------------------------------------------
# Main Renderer
# ----------------------------------------------------------
def render_analysis_tab(st, DOMAIN_COLORS):
    """Renders the Analysis & Reports tab."""
    ss = st.session_state

    st.header("📊 Post-Mission Analysis & Reporting")

    # --- THIS IS THE FIX (PART 1) ---
    # Check if a replay was triggered on the last run and show an info message.
    if ss.get("show_replay_message"):
        st.info("Replay loaded! **Click the '📡 Live / Simulation' tab now to view the event.** The simulation will be paused at the selected time.", icon="🎬")
        del ss.show_replay_message

    event_log = Path("results/reset_events.csv")
    if not event_log.exists() or event_log.stat().st_size == 0:
        st.info("No reset events logged yet. Run a simulation to generate events.")
        return

    try:
        df_events = pd.read_csv(event_log)
        if df_events.empty:
            st.info("No reset events have been logged yet."); return
        df_events = df_events.sort_values("timestamp", ascending=False).reset_index(drop=True)
    except Exception as e:
        st.error(f"Could not read the event log file: {e}"); return

    # --- Quick Stats Bar ---
    c = st.columns(4)
    c[0].metric("Total Events", len(df_events))
    c[1].metric("Last Timestamp [s]", f"{df_events['timestamp'].max():.2f}")
    c[2].metric("Mean R", f"{df_events['R'].mean():.4f}")
    c[3].metric("Mean Δθ [deg]", f"{df_events['predicted_benefit_deg'].mean():.2f}")
    st.markdown("---")

    # --- Domain Filter Bar ---
    st.markdown("#### Filter by Domain")
    cols = st.columns(len(DOMAIN_COLORS))
    active_domains = [dom for i, dom in enumerate(DOMAIN_COLORS) if cols[i].checkbox(dom, value=True, key=f"filter_{dom}")]
    df_filtered = df_events[df_events["domain"].isin(active_domains)]
    if df_filtered.empty: st.warning("No events match your filters."); return

    # --- Event Table (Cleaned and Simplified) ---
    st.markdown("### Logged Reset Opportunities")
    
    # Table Header
    header_cols = st.columns([1.2, 1, 1, 1, 1, 0.5])
    header_cols[0].markdown("**Domain**")
    header_cols[1].markdown("**Timestamp**")
    header_cols[2].markdown("**R**")
    header_cols[3].markdown("**Theta (deg)**")
    header_cols[4].markdown("**Benefit (deg)**")
    header_cols[5].markdown("**Replay**")

    # Table Rows
    for i, row in df_filtered.iterrows():
        cols = st.columns([1.2, 1, 1, 1, 1, 0.5])
        
        color = DOMAIN_COLORS.get(row["domain"], "#999")
        badge_html = f'<span class="event-badge" style="background-color:{color};">{row["domain"]}</span>'
        cols[0].markdown(badge_html, unsafe_allow_html=True)
        
        cols[1].text(f"{row['timestamp']:.2f}s")
        cols[2].text(f"{row['R']:.4f}")
        cols[3].text(f"{row['theta_net_deg']:.2f}°")
        cols[4].text(f"{row['predicted_benefit_deg']:.2f}°")

        # --- THIS IS THE FIX (PART 2) ---
        # When the button is clicked, set both the event data and the message flag.
        if cols[5].button("🎞️", key=f"replay_{i}", help="Replay this event"):
            ss.selected_event = dict(row)
            ss.show_replay_message = True # Set the flag to show the info message
            st.rerun()

    # --- Summary & Export sections ---
    st.markdown("---")
    st.markdown("### 📋 Summary by Domain")
    st.dataframe(make_summary_table(df_filtered), width='stretch')

    st.markdown("---")
    st.markdown("### 📜 Generate PDF Report")
    if st.button("Generate Report", width='stretch'):
        with st.spinner("Creating PDF report..."):
            report_path = Path("results/analysis_report.pdf")
            export_pdf(df_filtered, df_filtered, str(report_path))
            st.success(f"✅ Report saved to `{report_path}`")
            with open(report_path, "rb") as f:
                st.download_button("📥 Download PDF Report", f, "analysis_report.pdf", "application/pdf", width='stretch')
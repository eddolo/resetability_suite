# ==========================================================
# ui_analysis.py
# ----------------------------------------------------------
# Post-Mission Analysis & Reporting
# ==========================================================

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# --- NEW: Import the report generation utilities ---
from python.report_utils import export_pdf, make_summary
# --- Import from shared modules ---
from python.ui_helpers import make_summary_table


# ----------------------------------------------------------
# Main Renderer
# ----------------------------------------------------------
def render_analysis_tab(st, DOMAIN_COLORS):
    st.header("📊 Post-Mission Analysis & Reporting")
    event_log = Path("results/reset_events.csv")

    if not event_log.exists() or event_log.stat().st_size == 0:
        st.info("No reset events logged yet. Run a simulation to generate events.")
        return
    df_events = pd.read_csv(event_log)
    if df_events.empty:
        st.info("No reset events logged yet.")
        return

    df_events = df_events.sort_values("timestamp", ascending=False).reset_index(
        drop=True
    )

    # --- Quick Stats Bar ---
    # (No changes here)
    c = st.columns(4)
    c[0].metric("Total Events", len(df_events))
    c[1].metric("Last Timestamp [s]", f"{df_events['timestamp'].max():.2f}")
    c[2].metric("Mean R", f"{df_events['R'].mean():.4f}")
    c[3].metric("Mean Δθ [deg]", f"{df_events['predicted_benefit_deg'].mean():.2f}")
    st.markdown("---")

    # --- Domain Filter ---
    # (No changes here)
    st.markdown("#### Filter by Domain")
    cols = st.columns(len(DOMAIN_COLORS))
    active_domains = [
        dom
        for i, (dom, color) in enumerate(DOMAIN_COLORS.items())
        if cols[i].checkbox(dom, value=True, key=f"filter_{dom}")
    ]
    df_filtered = df_events[df_events["domain"].isin(active_domains)]
    if df_filtered.empty:
        st.warning("No events match your filters.")
        return

    # --- Event Table & Sparklines ---
    # (No changes here)
    st.markdown(
        "...Event table HTML/CSS...", unsafe_allow_html=True
    )  # Abridged for clarity
    # ... loop to display events ...

    # --- Summary Table ---
    # (No changes here)
    st.markdown("---")
    st.markdown("### 📋 Summary by Domain")
    summary_table = make_summary_table(df_filtered)
    st.dataframe(summary_table, use_container_width=True)

    # --- JSON Export ---
    # (No changes here)
    st.markdown("#### 📄 Summary (Export as JSON)")
    # ... JSON code and download button ...

    # ==========================================================
    # NEW: PDF Report Generation Section
    # ==========================================================
    st.markdown("---")
    st.markdown("### 📜 Generate PDF Report")
    st.caption(
        "Generate a formal PDF summary of the filtered reset events shown above."
    )

    if st.button("Generate Report", use_container_width=True):
        if df_filtered.empty:
            st.warning("No data to generate a report from. Please adjust filters.")
        else:
            with st.spinner("Creating PDF report..."):
                # 1. Create the summary dictionary using the utility
                summary_data = make_summary(df_filtered)

                # 2. Define the output path and ensure the directory exists
                report_path = Path("results/analysis_report.pdf")
                report_path.parent.mkdir(parents=True, exist_ok=True)

                # 3. Export the PDF
                export_pdf(summary_data, str(report_path))

                st.success(
                    f"✅ Report successfully generated and saved to `{report_path}`"
                )

                # 4. Offer the generated file for download
                with open(report_path, "rb") as f:
                    st.download_button(
                        label="📥 Download PDF Report",
                        data=f.read(),
                        file_name="analysis_report.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )

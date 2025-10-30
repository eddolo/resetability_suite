# ==========================================================
# ui_montecarlo.py
# ----------------------------------------------------------
# Monte Carlo Resetability Simulation
# ==========================================================

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# --- NEW: Import the report generation utilities ---
from python.report_utils import export_pdf, make_summary


# ==========================================================
# Main Renderer
# ==========================================================
def render_montecarlo_tab(st):
    """Render the Monte Carlo Simulation tab."""

    st.header("🧪 Monte Carlo Resetability Simulation")

    try:
        from python.montecarlo_robot import run_montecarlo, summarize_results

        st.caption("✅ Monte Carlo module loaded successfully.")
    except Exception as e:
        st.error(f"Could not import Monte Carlo module → {e}")
        return

    @st.cache_resource(show_spinner=True)
    def cached_montecarlo(n_runs, n_steps, noise_sigma, seed):
        return run_montecarlo(
            n_runs, n_steps=n_steps, noise_sigma=noise_sigma, seed=seed
        )

    with st.expander("⚙️ Simulation Settings", expanded=True):
        n_runs = st.slider("Number of runs", 50, 2000, 200, step=50)
        n_steps = st.slider("Steps per run", 20, 200, 80, step=10)
        noise_sigma = st.number_input("Noise σ (radians)", 0.0, 0.1, 0.02, step=0.005)
        seed = st.number_input("Random seed", 0, 9999, 0)
        run_btn = st.button("▶ Run Simulation", use_container_width='stretch')

    if run_btn:
        with st.spinner("Running Monte Carlo simulations..."):
            try:
                df = cached_montecarlo(n_runs, n_steps, noise_sigma, seed)
                summary = summarize_results(df)
            except Exception as e:
                st.error(f"Simulation failed: {e}")
                return

        st.success("✅ Simulation complete!")

        # --- Summary metrics, JSON, and Plots ---
        # (No changes here)
        st.markdown("### 📊 Summary Statistics")
        # ... metrics ...
        st.subheader("📄 Summary (JSON)")
        # ... json display ...
        st.subheader("📈 Distributions")
        # ... plots ...

        # ==========================================================
        # NEW & UPDATED: Export Section
        # ==========================================================
        st.markdown("---")
        st.subheader("💾 Export Results")

        # --- Existing CSV Export ---
        csv_path = Path("results") / "montecarlo_results.csv"
        csv_path.parent.mkdir(exist_ok=True)
        df.to_csv(csv_path, index=False)
        st.info(f"💾 Raw results saved to `{csv_path}`")
        with open(csv_path, "rb") as f:
            st.download_button(
                label="📥 Download Results CSV",
                data=f.read(),
                file_name="montecarlo_results.csv",
                mime="text/csv",
                use_container_width='stretch',
            )

        # --- New PDF Report Export ---
        st.markdown("---")
        st.info("📜 A formal PDF summary can also be generated.")

        # 1. Create summary data
        summary_data = make_summary(df)

        # 2. Define output path
        report_path = Path("results/montecarlo_report.pdf")

        # 3. Export PDF
        export_pdf(summary_data, str(report_path))

        # 4. Offer for download
        with open(report_path, "rb") as f:
            st.download_button(
                label="📥 Download PDF Report",
                data=f.read(),
                file_name="montecarlo_report.pdf",
                mime="application/pdf",
                use_container_width='stretch',
            )

    else:
        st.info("Adjust parameters above, then click ▶ Run Simulation to begin.")

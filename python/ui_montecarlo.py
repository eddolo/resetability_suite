# ==========================================================
# ui_montecarlo.py (Final, Complete, and Verified)
# ==========================================================
# Monte Carlo Resetability Simulation
# ==========================================================

from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# --- Import from the final, robust report utility ---
from python.report_utils import export_pdf

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
        n_runs = st.slider("Number of runs", 50, 2000, 200, step=50, key="mc_runs")
        n_steps = st.slider("Steps per run", 20, 200, 80, step=10, key="mc_steps")
        noise_sigma = st.number_input("Noise σ (radians)", 0.0, 0.1, 0.02, step=0.005, key="mc_noise")
        seed = st.number_input("Random seed", 0, 9999, 0, key="mc_seed")
        run_btn = st.button("▶ Run Simulation", width='stretch')

    if run_btn:
        with st.spinner("Running Monte Carlo simulations..."):
            try:
                # Use the keys to get the values from session state
                df = cached_montecarlo(st.session_state.mc_runs, st.session_state.mc_steps, st.session_state.mc_noise, st.session_state.mc_seed)
                summary = summarize_results(df)
            except Exception as e:
                st.error(f"Simulation failed: {e}")
                return

        st.success("✅ Simulation complete!")

        st.markdown("### 📊 Summary Statistics")
        c = st.columns(4)
        c[0].metric("Runs", st.session_state.mc_runs)
        c[1].metric("Steps per run", st.session_state.mc_steps)
        c[2].metric("Mean R", f"{df['R'].mean():.4f}")
        c[3].metric("Mean Δθ [deg]", f"{df['predicted_benefit_deg'].mean():.2f}")

        st.subheader("📄 Summary (JSON)")
        st.json(summary)

        st.subheader("📈 Distributions")
        fig, ax = plt.subplots(1, 3, figsize=(12, 3))
        ax[0].hist(df["R"], bins=30, color="blue", alpha=0.7); ax[0].set_title("R Distribution")
        ax[1].hist(df["theta_net_deg"], bins=30, color="orange", alpha=0.7); ax[1].set_title("θ_net [deg]")
        ax[2].hist(df["predicted_benefit_deg"], bins=30, color="green", alpha=0.7); ax[2].set_title("Predicted Benefit [deg]")
        plt.tight_layout(); st.pyplot(fig, clear_figure=True)

        # ==========================================================
        # Corrected Export Section
        # ==========================================================
        st.markdown("---")
        st.subheader("💾 Export Results")

        # --- CSV Export ---
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
                width='stretch',
            )

        # --- PDF Report Export ---
        st.markdown("---")
        report_path = Path("results/montecarlo_report.pdf")
        
        # The new export_pdf handles all summarizing and plotting internally.
        # For Monte Carlo data, the results and candidates are the same dataframe 'df'.
        export_pdf(df, df, str(report_path))
        
        st.info(f"📜 PDF report saved to `{report_path}`")
        with open(report_path, "rb") as f:
            st.download_button(
                label="📥 Download PDF Report",
                data=f.read(),
                file_name="montecarlo_report.pdf",
                mime="application/pdf",
                width='stretch',
            )
            
    else:
        st.info("Adjust parameters above, then click ▶ Run Simulation to begin.")
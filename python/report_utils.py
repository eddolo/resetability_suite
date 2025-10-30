# python/report_utils.py (Version 3 - Final, Robust Version)
import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import matplotlib.pyplot as plt
from io import BytesIO

def make_summary(df_clean):
    """Calculates statistics from a pre-cleaned dataframe."""
    if df_clean.empty:
        return {"Mean R": 0.0, "Mean Theta [deg]": 0.0, "Mean Benefit [deg]": 0.0, "Reset Opportunities Found": 0}
    
    return {
        "Mean R": np.nanmean(df_clean["R"]),
        "Mean Theta [deg]": np.nanmean(df_clean["theta_net_deg"]),
        "Mean Benefit [deg]": np.nanmean(df_clean["predicted_benefit_deg"]),
        "Reset Opportunities Found": len(df_clean),
    }

def create_report_plot_from_clean_data(df_clean, is_dense_timeline):
    """Creates a plot from a pre-cleaned dataframe."""
    if df_clean.empty:
        return None

    fig, ax1 = plt.subplots(figsize=(8, 3))
    
    if is_dense_timeline:
        # For auto-reports from the Live/Sim tab (continuous data)
        ax1.plot(df_clean["timestamp"], df_clean["R"], color="blue", alpha=0.7, label="R")
        ax1.set_xlabel("Time [s]")
        ax1.set_ylabel("R", color="blue")
        ax2 = ax1.twinx()
        ax2.plot(df_clean["timestamp"], df_clean["theta_net_deg"], color="orange", alpha=0.7, label="θ_net [deg]")
        ax2.set_ylabel("θ_net [deg]", color="orange")
        if not df_clean.empty:
             ax1.scatter(df_clean["timestamp"], df_clean["R"], color="red", s=40, zorder=5, label="Reset Opportunity")
    else:
        # For reports from the Analysis tab (sparse events)
        # Manually set axis limits to guarantee all points are visible.
        if not df_clean.empty:
            min_r, max_r = df_clean["R"].min(), df_clean["R"].max()
            min_theta, max_theta = df_clean["theta_net_deg"].min(), df_clean["theta_net_deg"].max()
            r_padding = (max_r - min_r) * 0.15 + 1e-5
            theta_padding = (max_theta - min_theta) * 0.15 + 1e-5
            ax1.set_ylim(min_r - r_padding, max_r + r_padding)
            ax1.set_xlim(min_theta - theta_padding, max_theta + theta_padding)

        ax1.scatter(df_clean["theta_net_deg"], df_clean["R"], color="red", s=50, zorder=5, label="Reset Opportunity")
        ax1.set_xlabel("θ_net [deg]")
        ax1.set_ylabel("R", color="blue")
        ax1.grid(True, linestyle='--', alpha=0.6)
        
        for i, row in df_clean.iterrows():
            ax1.annotate(f"t={row['timestamp']:.1f}s", (row['theta_net_deg'], row['R']), textcoords="offset points", xytext=(0,10), ha='center', fontsize=8)

    ax1.set_title("Resetability Analysis Summary")
    ax1.legend(loc="upper right")
    plt.tight_layout()
    
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)
    return ImageReader(buf)

def export_pdf(results_df, candidates_df, outfile="results/telemetry_report.pdf"):
    """
    Exports a PDF report. This is the main function that cleans the data
    and then calls helpers to generate the summary and plot.
    """
    # --- THIS IS THE FIX ---
    # 1. Determine the data type and create a single, clean source of truth.
    is_dense_timeline = len(results_df) > 50
    
    # We use 'candidates_df' as the source for the Analysis tab report.
    # We clean it by replacing non-finite numbers (inf) with NaN, then dropping any row with NaN.
    df_to_process = candidates_df if not is_dense_timeline else results_df
    df_clean = df_to_process.replace([np.inf, -np.inf], np.nan).dropna(
        subset=['R', 'theta_net_deg', 'predicted_benefit_deg', 'timestamp']
    )

    # 2. Generate summary and plot using ONLY the clean data.
    summary_data = make_summary(df_clean)
    plot_image = create_report_plot_from_clean_data(df_clean, is_dense_timeline)

    # 3. Assemble the PDF.
    c = canvas.Canvas(outfile, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, "SO(3) Resetability Analysis Report")
    c.line(72, height - 80, width - 72, height - 80)
    c.setFont("Helvetica", 12)
    y_position = height - 120
    for key, value in summary_data.items():
        text = f"{key}: {value:.4f}" if isinstance(value, float) else f"{key}: {value}"
        c.drawString(82, y_position, text)
        y_position -= 20
    
    if plot_image:
        img_width, img_height = plot_image.getSize()
        aspect = img_height / float(img_width)
        draw_width = width - 144
        draw_height = draw_width * aspect
        c.drawImage(plot_image, 72, y_position - draw_height - 20, width=draw_width, height=draw_height)

    c.save()
    return outfile
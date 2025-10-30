# python/report_utils.py (Version 2 with Plots)
import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import matplotlib.pyplot as plt
from io import BytesIO

def make_summary(df):
    """Calculates summary statistics, correctly handling potential NaN values."""
    if df.empty:
        return {"Mean R": np.nan, "Mean Theta [deg]": np.nan, "Mean Benefit [deg]": np.nan, "Reset Opportunities Found": 0}
    
    # --- THIS IS THE FIX ---
    # Before, we just counted all rows. Now, we only count rows that have
    # valid, finite numbers for the columns we are going to plot.
    plottable_candidates = df.dropna(subset=['R', 'theta_net_deg', 'predicted_benefit_deg'])
    
    return {
        "Mean R": np.nanmean(plottable_candidates["R"]),
        "Mean Theta [deg]": np.nanmean(plottable_candidates["theta_net_deg"]),
        "Mean Benefit [deg]": np.nanmean(plottable_candidates["predicted_benefit_deg"]),
        "Reset Opportunities Found": len(plottable_candidates), # Now this count is honest.
    }

def create_report_plot(results_df, candidates_df):
    """Creates a Matplotlib plot and returns it as an in-memory image object."""
    if results_df.empty:
        return None

    fig, ax1 = plt.subplots(figsize=(8, 3))
    
    # --- Smart Plotting Logic ---
    is_dense_timeline = len(results_df) > 50

    if is_dense_timeline:
        # This is for the auto-report from the Live/Sim tab (continuous data)
        ax1.plot(results_df["timestamp"], results_df["R"], color="blue", alpha=0.7, label="R")
        ax2 = ax1.twinx()
        ax2.plot(results_df["timestamp"], results_df["theta_net_deg"], color="orange", alpha=0.7, label="θ_net [deg]")
        ax2.set_ylabel("θ_net [deg]", color="orange")
        ax2.tick_params(axis='y', labelcolor='orange')
    else:
        # This is for the report from the Analysis tab (sparse events)
        # We will plot R vs. theta_net on a scatter plot.
        
        # --- Manually calculate plot limits to ensure all points are visible ---
        if not results_df.empty:
            # Find the min/max of the data
            min_r, max_r = results_df["R"].min(), results_df["R"].max()
            min_theta, max_theta = results_df["theta_net_deg"].min(), results_df["theta_net_deg"].max()
            
            # Add a 10% padding to the range
            r_padding = (max_r - min_r) * 0.1 + 1e-6 # Add a tiny value to avoid zero range
            theta_padding = (max_theta - min_theta) * 0.1 + 1e-6
            
            # Set the axis limits manually
            ax1.set_ylim(min_r - r_padding, max_r + r_padding)
            ax1.set_xlim(min_theta - theta_padding, max_theta + theta_padding)

        ax1.scatter(results_df["theta_net_deg"], results_df["R"], color="red", s=50, zorder=5, label="Reset Opportunity")
        ax1.set_xlabel("θ_net [deg]")
        ax1.set_ylabel("R", color="blue")
        ax1.tick_params(axis='y', labelcolor='blue')
        ax1.grid(True, linestyle='--', alpha=0.6)
        
        # Annotate points with their timestamps
        for i, row in results_df.iterrows():
            ax1.annotate(f"t={row['timestamp']:.1f}s", (row['theta_net_deg'], row['R']), textcoords="offset points", xytext=(0,10), ha='center', fontsize=8)

    ax1.set_title("Resetability Analysis Summary")
    ax1.legend(loc="upper right")
    plt.tight_layout()
    
    # Save to buffer and return
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)
    
    return ImageReader(buf)

def export_pdf(summary_data, results_df, candidates_df, outfile="results/telemetry_report.pdf"):
    """Exports a PDF report including summary data and a plot."""
    c = canvas.Canvas(outfile, pagesize=letter)
    width, height = letter

    # --- Title ---
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, "SO(3) Resetability Analysis Report")
    c.setStrokeColorRGB(0.1, 0.1, 0.1)
    c.line(72, height - 80, width - 72, height - 80)

    # --- Summary Metrics ---
    c.setFont("Helvetica", 12)
    y_position = height - 120
    for key, value in summary_data.items():
        if isinstance(value, float):
            text = f"{key}: {value:.4f}"
        else:
            text = f"{key}: {value}"
        c.drawString(82, y_position, text)
        y_position -= 20

    # --- Generate and Draw Plot ---
    plot_image = create_report_plot(results_df, candidates_df)
    
    if plot_image:
        # Draw the plot on the PDF, leaving some margin
        # The plot is 8x3 inches at 150 DPI = 1200x450 pixels. We scale it down.
        img_width, img_height = plot_image.getSize()
        aspect = img_height / float(img_width)
        draw_width = width - 144 # Full page width with 1-inch margins
        draw_height = draw_width * aspect
        
        c.drawImage(plot_image, 72, y_position - draw_height - 20, width=draw_width, height=draw_height)

    c.save()
    return outfile
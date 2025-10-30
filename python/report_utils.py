# python/report_utils.py (Final, Verified Version)
import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime

def _create_report_plot(df_clean, is_dense_timeline):
    if df_clean.empty: return None
    fig, ax1 = plt.subplots(figsize=(7, 2.5), dpi=150)
    
    if is_dense_timeline:
        ax1.plot(df_clean["timestamp"], df_clean["R"], color="#4A90E2", alpha=0.7, label="R")
        ax1.set_xlabel("Time [s]"); ax1.set_ylabel("R", color="#4A90E2")
        ax2 = ax1.twinx()
        ax2.plot(df_clean["timestamp"], df_clean["theta_net_deg"], color="#F5A623", alpha=0.7, label="θ_net [deg]")
        ax2.set_ylabel("θ_net [deg]", color="#F5A623")
        candidates = df_clean[(df_clean["R"] < 0.05) & (df_clean["predicted_benefit_deg"] > 0)]
        if not candidates.empty: ax1.scatter(candidates["timestamp"], candidates["R"], color="#D0021B", s=30, zorder=5, label="Reset Opportunity")
    else:
        if not df_clean.empty:
            min_r, max_r = df_clean["R"].min(), df_clean["R"].max()
            min_theta, max_theta = df_clean["theta_net_deg"].min(), df_clean["theta_net_deg"].max()
            r_pad = (max_r - min_r) * 0.2 + 1e-5; theta_pad = (max_theta - min_theta) * 0.2 + 1e-5
            ax1.set_ylim(min_r - r_pad, max_r + r_pad); ax1.set_xlim(min_theta - theta_pad, max_theta + theta_pad)
        ax1.scatter(df_clean["theta_net_deg"], df_clean["R"], color="#D0021B", s=40, zorder=5, label="Reset Opportunity")
        ax1.set_xlabel("θ_net [deg]"); ax1.set_ylabel("R", color="#4A90E2")
        ax1.grid(True, linestyle='--', alpha=0.6)
        for i, row in df_clean.iterrows():
            ax1.annotate(f"t={row['timestamp']:.1f}s", (row['theta_net_deg'], row['R']), textcoords="offset points", xytext=(0,10), ha='center', fontsize=7)

    ax1.set_title("Resetability Analysis Summary"); ax1.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    buf = BytesIO(); fig.savefig(buf, format='png'); buf.seek(0); plt.close(fig)
    return buf

def export_pdf(results_df, candidates_df, outfile="results/telemetry_report.pdf"):
    doc = SimpleDocTemplate(outfile, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("SO(3) Resetability Analysis Report", styles['h1']))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 0.25 * inch))

    is_dense_timeline = len(results_df) > 50
    df_to_process = candidates_df if not is_dense_timeline else results_df
    df_clean = df_to_process.replace([np.inf, -np.inf], np.nan).dropna(
        subset=['R', 'theta_net_deg', 'predicted_benefit_deg', 'timestamp']
    )

    story.append(Paragraph("Overall Summary", styles['h2']))
    if not df_clean.empty:
        summary_data = {
            "Mean R": np.nanmean(df_clean["R"]), "Mean Theta [deg]": np.nanmean(df_clean["theta_net_deg"]),
            "Mean Benefit [deg]": np.nanmean(df_clean["predicted_benefit_deg"]), "Reset Opportunities Found": len(df_clean),
        }
        for key, value in summary_data.items():
            text = f"<b>{key}:</b> {value:.4f}" if isinstance(value, float) else f"<b>{key}:</b> {value}"
            story.append(Paragraph(text, styles['BodyText']))
    else: story.append(Paragraph("No valid data to summarize.", styles['BodyText']))
    story.append(Spacer(1, 0.25 * inch))

    story.append(Paragraph("Visual Summary", styles['h2']))
    plot_buf = _create_report_plot(df_clean, is_dense_timeline)
    if plot_buf:
        # --- THIS IS THE FIX ---
        # Use the Image class, which correctly handles in-memory buffers.
        img = Image(plot_buf, width=7*inch, height=2.5*inch)
        story.append(img)
    else: story.append(Paragraph("No data to plot.", styles['BodyText']))
    story.append(Spacer(1, 0.25 * inch))

    story.append(Paragraph("Detailed Event Log (Top 10 by Benefit)", styles['h2']))
    if not df_clean.empty and not is_dense_timeline:
        top_events = df_clean.sort_values(by='predicted_benefit_deg', ascending=False).head(10)
        table_data = [["Timestamp (s)", "R", "Theta (deg)", "Benefit (deg)"]]
        for _, row in top_events.iterrows():
            table_data.append([f"{row['timestamp']:.2f}", f"{row['R']:.4f}", f"{row['theta_net_deg']:.2f}", f"{row['predicted_benefit_deg']:.2f}"])
        t = Table(table_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.darkslategray), ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('BOTTOMPADDING', (0,0), (-1,0), 10),
            ('BACKGROUND', (0,1), (-1,-1), colors.ghostwhite), ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        story.append(t)
    else: story.append(Paragraph("No discrete events to tabulate.", styles['BodyText']))

    doc.build(story)
    return outfile